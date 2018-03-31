import os
import BlockDevice
import struct
import numpy as np
from File import *
from INode import *
from enum import Enum

# Global constants
default_blocksize = 1024
default_blockcount = 1024


class FileSystem:
    """
    Central FileSystem class. Objects can be constructed via 
    createFileSystem or mount, which forms a new object in memory and loads 
    a FileSystem object from memory respectively.

    upon mounting and unmounting, unpack and unpack methods are called on
    the FileSystem object's component objects to load/store from/to disk respectively

    Meant to be the only class the user (shell.py in this case) interfaces with, 
    aside from mount and unmount, provides a set of methods that access the component
    objects of the file system
    """

    @staticmethod
    def createFileSystem(filename, blockcount=default_blockcount, blocksize=default_blocksize):
        newFS = FileSystem(filename=filename, blockcount=blockcount, blocksize=blocksize)

        blocksToAlloc = newFS.masterBlock.inodeMapAddress+newFS.masterBlock.inodeCount

        if blocksToAlloc > newFS.masterBlock.blockCount:
            print("Error: createFileSystem(): not enough blocks to create file system \n")
            print("File System was not saved")
            return

        #initial configuration of blockMap, and inodeMap block allocations
        for i in range(blocksToAlloc):
            newFS.blockMap.allocateBlock()

        newFS.unmount()

    def __init__(self, filename, blockcount=default_blockcount, blocksize=default_blocksize):
        self.fileName = filename
        self.masterBlock = MasterBlock(pFS=self, blockcount=blockcount, blocksize=blocksize)
        self.blockMap = BlockMap(self)
        self.inodeMap = InodeMap(self)
        self.blockCache = {}
        self.rBlockDev = None
        self.currentDir = None
    #load block from cache, load into cache if not availble
    def retrieveBlock(self,blockNum,dirty=False):

        if blockNum not in self.blockCache:
            retBlock = bytearray(self.masterBlock.blockSize)
            self.rBlockDev.read_block(blockNum, retBlock)
            self.blockCache[blockNum] = (retBlock, dirty)
        if (not(self.blockCache[blockNum])[1]) and dirty:
            self.blockCache[blockNum] = ((self.blockCache[blockNum])[0],dirty)
        return (self.blockCache[blockNum])[0]

    def cacheBlock(self,blockNum,block):
        self.blockCache[blockNum] = (block,True)
        return

    @staticmethod
    def mount(filename):
        newFS = FileSystem(filename,
                           blocksize=BlockDevice.BlockDevice.filename_to_blocksize(filename))
        newFS.rBlockDev = BlockDevice.BlockDevice(filename=filename,
                                           blocksize=newFS.masterBlock.blockSize, blockCount=1, create=False)
        newFS.masterBlock.unpack(newFS.rBlockDev)
        # must update blockDev with correct size of read from disk (num_blocks) data from masterBlock unpacked
        newFS.rBlockDev.num_blocks = newFS.masterBlock.blockCount
        newFS.blockMap.unpack(newFS.rBlockDev)
        newFS.inodeMap.unpack(newFS.rBlockDev)
        newFS.currentDir = Directory(newFS.inodeMap.inodeMap[newFS.masterBlock.rootDirAddress],None)
        return newFS

    def unmount(self,softUnmount = False):
        if self.rBlockDev is not None and softUnmount is not True:
            self.rBlockDev.close()
        blockDev = BlockDevice.BlockDevice(filename=self.fileName, blocksize=int(self.masterBlock.blockSize),
                                           blockCount=self.masterBlock.blockCount,
                                           create=True)
        blockDev.write_block(0, self.masterBlock.pack(), True)
        self.blockMap.pack(blockDev)
        self.inodeMap.pack(blockDev)

        for key in self.blockCache:
            if (self.blockCache[key])[1]:
                blockDev.write_block(key, (self.blockCache[key])[0], True)

        print("FileSystem has been saved as: " + blockDev.filename)

        blockDev.close()

    # TODO: part of Assignment 3.2:
    def namei(self, path):
        """
        Return the INode structure corresponding to path
        :param path: path of a file or directory
        :return: INode structure
        """
        retNode = self.currentDir.inode
        retParent = self.currentDir.parent

        if(path is None):
            print("path is none")
            return retNode, retParent

        pathList = path.split("/")
        for word in pathList:
            if not retNode.isDirectoy:
                print("Error: part in path is not a directory")
                return None, None
            searchDir = Directory(retNode,retParent)
            sResult = searchDir.get_children()
            if word in sResult:
                retParent = retNode
                retNode = sResult[word].inode
            else:
                print("Error: part in path does not exist")
                return None, None

        return retNode,retParent

    # ========User Functions==========

    # TODO: part of Assignment 3.2:
    def open(self, path, mode):
        """
        Return a File object corresponding to "path", opened for either
        reading, writing, creating or appending.
        Model your semantics of these flags on the Python documentation here:
        https://docs.python.org/3/library/functions.html#open
        :param path:   path to the file we want to open
        :param mode:   "r", "w", or "a"
        :return:       File object, or None if there is no such file (or it's a directory)
        """
        fileInode, fileParent = self.namei(path)
        if fileInode is None:
            return None
        if not fileInode.isFile():
            print("Error: file to read from is actually a directory")
            return None
        return File(fileInode, fileParent)

    def splitPathName(self,path):
        pathList = path.split("/")
        newPath = "/".join(pathList[:-1])
        if newPath == '':
            return None, (pathList[-1:])[0]
        return newPath, (pathList[-1:])[0]

    def printDir(self,path = None):
        dirInode, dirParent = self.namei(path)
        if dirInode is None:
            return
        if not dirInode.isDirectory():
            print("Error: directory is actually a file")
            return
        print("|||dirInode: " + str(dirInode.inodeNum))
        if(dirParent is not None):
            print("parentInode:" + str(dirParent))
        dir = Directory(dirInode, dirParent)
        print("ls Test")
        print(dir.get_children())
        for key in dir.get_children():
            print("ls Test2")
            print(key)

    def printFile(self,path, length = 100):
        file = self.open(path,"r")
        if file is None:
            return
        readBuffer = bytearray(length)
        file.read(bytearray(length))
        print(readBuffer.decode("utf-8"))

    def writeFile(self,path, message, offset=-1):
        file = self.open(path,"w")
        if file is None:
            return
        if offset != -1:
            file.seek(offset)
        file.write(message.encode("utf-8"))

    def makeFSObj(self, path, newType):
        newPath, name = self.splitPathName(path)
        dirInode, dirParent = self.namei(newPath)
        print("dirInode: " + str(dirInode.inodeNum))
        if(dirParent is not None):
            print("parentInode:" + str(dirParent))
        if dirInode is None:
            return
        if not dirInode.isDirectory():
            print("Error: directory is actually a file")
            return
        dir = Directory(dirInode, dirParent)
        dirChildren = dir.get_children()
        if dirChildren:
            if name in dirChildren:
                print("Error: file or directory  with that name already exists")
                return
        allocInode = self.inodeMap.inodeMap[self.inodeMap.allocateInode(newType)]
        print("alloc: " + str(allocInode.inodeNum))
        dir.add_child(name, allocInode)
        if newType == "d":
            dir = Directory(allocInode, dir.inode)
            dir.add_child(".", dir.inode)
            dir.add_child("..", dir.parent)

    def makeDir(self,path):
        self.makeFSObj(path, "d")

    def makeFile(self,path):
        self.makeFSObj(path, "f")

    def moveCurrDir(self,path):
        dirInode, dirParent = self.namei(path)
        if dirInode is None:
            return
        if not dirInode.isDirectory():
            print("Error: directory is actually a file")
            return
        self.currentDir = Directory(dirInode, dirParent)

    def printBlockMap(self):
        self.blockMap.printBlockMap()

    def allocBlock(self):
        return self.blockMap.allocateBlock()

    def freeBlock(self, blockNum):
        self.blockMap.freeBlock(blockNum)

    def printINodeMap(self):
        self.inodeMap.printInodeMap()

    def allocINode(self, typeName):
        try:
            self.inodeMap.allocateInode(INodeType(ord(typeName)))
        except ValueError:
            print("Error: alloc_inode - invalid state try O,f,d,s")

    def freeINode(self, inodeNum):
        self.inodeMap.freeInode(inodeNum)


class MasterBlock:
    # Masterblock constants
    default_inodecount = 256
    default_blockmapaddress = 1 # starts after master block
    default_inodemapaddress = 2 # starts after blockMap
    default_magicNumber = 0x700154ED
    default_rootdiraddr = 0
    default_flags = 'X'

    def __init__(
            self, pFS,
            magicnumber=default_magicNumber,
            blocksize=default_blocksize,
            blockcount=default_blockcount,
            inodecount=default_inodecount,
            blockmapaddress=default_blockmapaddress,
            inodemapaddress=default_inodemapaddress,
            rootdiraddress=default_rootdiraddr,
            flag=default_flags
    ):
        self.parentFS = pFS
        self.magicNumber = magicnumber
        self.blockSize = blocksize
        self.blockCount = blockcount
        self.inodeCount = int(inodecount)
        self.blockMapAddress = blockmapaddress
        self.flags = flag
        self.blockMapBlockCount = cielDiv(cielDiv(self.blockCount, 8), self.blockSize)
        self.inodeMapAddress = self.blockMapAddress + self.blockMapBlockCount
        self.rootDirAddress = 0

    def pack(self):
        return bytearray(struct.pack("=ihihiiic",
                                     self.magicNumber,  # 32 bits
                                     self.blockSize,  # 16 bits
                                     self.blockCount,  # 32 bits
                                     self.inodeCount,  # 16 bits
                                     self.blockMapAddress,  # 32 bits
                                     self.inodeMapAddress,  # 32 bits
                                     self.rootDirAddress,  # 32 bits
                                     bytes(self.flags, "utf8")))  # 8 bits, char format

    def unpack(self, blockDev):
        # 0-24 are the 25 bytes of the master blcok
        readBArray = bytearray(self.blockSize)
        blockDev.read_block(0, readBArray)
        (self.magicNumber,
         self.blockSize,
         self.blockCount,
         self.inodeCount,
         self.blockMapAddress,
         self.inodeMapAddress,
         self.rootDirAddress,
         self.flags) = struct.unpack("=ihihiiic", readBArray[:25])
        # decode from utf8 encoding to python string
        self.flags = self.flags.decode("utf8")


class BlockMap:

    def __init__(self, parentFS):
        self.parentFS = parentFS
        self.masterBlock = self.parentFS.masterBlock
        self.blockMap = [False] * self.masterBlock.blockCount

    def setBlock(self, blockID, newState):
        """
        attempts to set a block in the blockmap to the sepecified state,
        prints error if attempt fails
        """
        if blockID > self.masterBlock.blockCount:
            print("Error: BlockMap.setBlock(): blockID greater than file system's blockCount.")
            return False
        if self.blockMap[blockID] is True:
            if newState is False:
                self.blockMap[blockID] = False
                return True
            else:
                print("Error: BlockMap.setBlock(): A Block already exists at specified blockID.")
                return False
        self.blockMap[blockID] = newState
        return True

    def allocateBlock(self):
        """
        returns block number(i) of allocated block if successful, -1 otherwise
        the allocated block is always the first open one in the blockmap.
        """
        for i in range(0, self.masterBlock.blockCount):
            if not self.blockMap[i]:
                if self.setBlock(i, True):
                    #print("Allocated Block " + str(i) + ".\n")
                    return i
                else:
                    print("Error BlockMap.allocateBlock()")
                    return -1
        print("Error BlockMap.allocateBlock(): BlockMap full")
        return -1

    def freeBlock(self, blockID):
        if not self.setBlock(blockID, False):
            print("Error BlockMap.freeBlock()")
            return False
        return True

    def printBlockMap(self):
        """
        Prints block state in 8 wide chunks seperated by '|'
        every 64 blocks the printed map is taken to a new line
        """
        printStr = ""
        for x in range(self.masterBlock.blockCount):
            if self.blockMap[x]:
                printStr = printStr + "1"
            else:
                printStr = printStr + "0"
            if (x + 1) % 8 == 0:
                printStr = printStr + "|"
            if (x + 1) % 64 == 0:
                printStr = printStr + "\n"
        print(printStr)

    def pack(self, blockDev):
        """
        since 8 block map entries are being stored per byte, the range
        is set to end at an eigth the total block count since i represents
        bytes to be written.
        """
        blockMapBytes = bytearray(np.packbits(self.blockMap))
        # write to block [1,(blockCount//8)//blockSize]
        for i in range(0, self.masterBlock.blockCount // 8, self.masterBlock.blockSize):
            blockDev.write_block(1 + i // self.masterBlock.blockSize,
                                 blockMapBytes[i:i + self.masterBlock.blockSize - 1], True)
        return

    def unpack(self, blockDev):
        """
        on unpack (as part of unmount) we must update our masterblock reference and inital blockmap size

        we read and unpack a block of the block map at a time. For each block from memory
        we free the blocksize*8 bools into the blockmap until the maxium block map index is reached

        if we run out of stored blocks before filling the block map, we print an error
        """
        self.masterBlock = self.parentFS.masterBlock
        self.blockMap = [False] * self.masterBlock.blockCount
        blockMapBuffer = bytearray(self.masterBlock.blockSize)
        for i in range(0, self.masterBlock.blockCount // 8, self.masterBlock.blockSize):
            blockDev.read_block(1 + i // self.masterBlock.blockSize, blockMapBuffer)
            blockMapValues = np.unpackbits(blockMapBuffer)
            for x in range(i * 8, (i + self.masterBlock.blockSize) * 8, 1):
                if x >= self.masterBlock.blockCount:
                    return
                self.blockMap[x] = blockMapValues[x]
        print("BlockMap:unpack:Error - Block map not filled from memory")



class InodeMap:

    def __init__(self, parentFS):
        self.parentFS = parentFS
        self.masterBlock = self.parentFS.masterBlock
        self.inodeMap = [INode(parentFS, x) for x in range(self.masterBlock.inodeCount)]
        self.setInode(self.masterBlock.rootDirAddress, INodeType.DIRECTORY)

    def setInode(self, inodeID, newState):
        if (inodeID > self.masterBlock.inodeCount):
            print("Error: InodeMap.setInode(): inodeID greater than file system's inodeCount.")
            return False
        if self.inodeMap[inodeID].flags != INodeType.FREE:
            if (newState == INodeType.FREE):
                self.inodeMap[inodeID].flags = INodeType.FREE
                return True
            else:
                print("Error: InodeMap.setInode(): An inode already exists at specified inodeID.")
                return False
        self.inodeMap[inodeID].flags = newState
        return True

    def allocateInode(self, type):
        """
        returns block number(i) of allocated block if successful, -1 otherwise
        """
        try:
            newInodeType = INodeType(ord(type))
        except:
            print("Error: allocateInode: Invalid Inode type given")
            return -1

        for i in range(0, self.masterBlock.inodeCount):
            if self.inodeMap[i].flags == INodeType.FREE:
                if self.setInode(i, newInodeType):
                    print("Allocated Inode at " + str(i) + " to state" + type + ".\n")
                    return i
                else:
                    print("Error inodeMap.allocateInode()")
                    return -1
        print("Error inodeMap.allocateInode(): inodeMap full")
        return -1

    def freeInode(self, inodeID):
        if not self.setInode(inodeID, INodeType.FREE):
            print("Error inodeMap.freeInode()")
            return False
        return True

    def printInodeMap(self):
        """
        Prints inode state in 8 wide chunks seperated by '|'
        every 64 inodes the printed map is taken to a new line
        """
        printStr = ""
        for x in range(self.masterBlock.inodeCount):
            printStr = printStr + chr(self.inodeMap[x].flags)
            if (x + 1) % 8 == 0:
                printStr = printStr + "|"
            if (x + 1) % 64 == 0:
                printStr = printStr + "\n"
        print(printStr)

    def pack(self, blockDev):
        startIndex = 1 + self.masterBlock.blockMapBlockCount
        for i in range(self.masterBlock.inodeCount):
            self.inodeMap[i].pack(blockDev, startIndex + i)

    def unpack(self, blockDev):
        """
        on unpack (as part of unmount) we must update our masterblock reference and inital blockmap size

        we unpack every inode, starting at block after blockmap
        """
        self.masterBlock = self.parentFS.masterBlock

        startIndex = 1 + self.masterBlock.blockMapBlockCount
        for i in range(0, self.masterBlock.inodeCount, ):
            self.inodeMap[i].unpack(blockDev, startIndex + i)

#integer divide x by y and return next highest (toward infinities) integer
def cielDiv(x,y):
    return -(-x//y)

''' Saved for later
class Block:

    def __init__(self):

    def pack():


    def unpack(blockDev):
'''


# ============Nosetests=========================
#=============|As. 2|=====================
def test_consistent_values_I():
    FileSystem.createFileSystem("test", 2048)
    testFS = FileSystem.mount("test.dev")
    assert testFS.masterBlock.blockCount == 2048, "blockCount should be 2048 has specified"


def test_consistent_values_II():
    FileSystem.createFileSystem("testII", 2048, 2048)
    testFS = FileSystem.mount("testII.2048.dev")
    assert testFS.masterBlock.blockCount == 2048, "blockCount should be 2048 has specified"
    assert testFS.masterBlock.blockSize == 2048, "blockSize should be 2048 has specified"


def test_mount_unmount_mount():
    FileSystem.createFileSystem("testIII", 2048, 2048)
    testFS = FileSystem.mount("testIII.2048.dev")

    testFS.blockMap.allocateBlock()  # should allocate at block 3
    assert testFS.blockMap.blockMap[2] == 1

    testFS.inodeMap.allocateInode("d")  # shoud allocate at inode 1
    assert testFS.inodeMap.inodeMap[0].flags == INodeType.DIRECTORY

    testFS.unmount()
    testFS = FileSystem.mount("testIII.2048.dev")

    assert testFS.blockMap.blockMap[2] == 1

    assert testFS.inodeMap.inodeMap[0].flags == INodeType.DIRECTORY

    assert testFS.masterBlock.blockCount == 2048, "blockCount should be 2048 has specified"
    assert testFS.masterBlock.blockSize == 2048, "blockSize should be 2048 has specified"


def test_free_block():
    FileSystem.createFileSystem("testIV", 2048, 2048)
    testFS = FileSystem.mount("testIV.2048.dev")

    testFS.blockMap.allocateBlock()
    testFS.blockMap.allocateBlock()
    testFS.blockMap.allocateBlock()
    testFS.blockMap.allocateBlock()
    testFS.blockMap.allocateBlock()

    for i in range(5):
        assert testFS.blockMap.blockMap[i] == 1

    testFS.freeBlock(2)

    assert testFS.blockMap.blockMap[2] == 0


def test_free_inode():
    FileSystem.createFileSystem("testV", 2048, 2048)
    testFS = FileSystem.mount("testV.2048.dev")

    testFS.inodeMap.allocateInode("d")
    testFS.inodeMap.allocateInode("d")
    testFS.inodeMap.allocateInode("d")
    testFS.inodeMap.allocateInode("d")
    testFS.inodeMap.allocateInode("d")

    for i in range(5):
        assert testFS.inodeMap.inodeMap[i].flags == INodeType.DIRECTORY

    testFS.inodeMap.freeInode(2)

    assert testFS.inodeMap.inodeMap[2].flags == INodeType.FREE

#=============|As. 3mnbbm|=====================

def test_write_and_read():
    FileSystem.createFileSystem("testVI", 2048, 2048)
    testFS = FileSystem.mount("testV.2048.dev")

    testFS.inodeMap.allocateInode("f")
    testInode = testFS.inodeMap.inodeMap[0]

    testInode.truncate(27624)
    testInode.level = 1

    testWrite = "A cat is Here".encode('ascii')

    testInode.write(testWrite, 27124)

    testFS.unmount()

    testFS = FileSystem.mount("testV.2048.dev")

    testRead = bytearray(len("A cat is Here"))

    testInode.read(testRead, 27124)


    assert str(testRead.decode("ascii")) == "A cat is Here"