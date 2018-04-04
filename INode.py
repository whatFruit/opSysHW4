from FileSystem import *
from enum import Enum
import struct

class INodeType(Enum):
    FREE = ord("O")
    FILE = ord("f")
    DIRECTORY = ord("d")
    SYMLINK = ord("s")

class INode:
    # Inode Constants
    Num_Block_Ptrs = 26
    default_date = 777
    default_flags_inode = INodeType.FREE
    default_perms = 777
    default_level = 0
    default_length = 2048
    default_MagicNumber = 5000

    def __init__(self, parentFS,
                 inodenum, flags=default_flags_inode,
                 date=default_date,
                 perms=default_perms,
                 level=default_level,
                 length=default_length,
                 magicNumber = default_MagicNumber):
        self.parentFS = parentFS
        self.masterBlock = self.parentFS.masterBlock
        self.inodeNum = inodenum  # 16bits
        self.cdate = date  # 32bits
        self.mdate = date  # 32bits
        self.flags = flags  # 8bits
        self.perms = perms  # 16bits
        self.level = level  # 8bits
        self.length = length # 32bits
        self.magicNumber = magicNumber # 32 bits
        self.blockPtrs = [0] * INode.Num_Block_Ptrs  # 28 x 32bits
        self.ptrsPerBlock = self.masterBlock.blockSize // 4

    ########### Exported functions

    # TODO: Assignment 3.2
    #    Tricky bits: both the file_offset and the buffer_len might not
    #    (probably won't be) block aligned.
    #    Read the blocks that are covered by this request, then copy the bytes
    #    from those blocks into buffer. Write tests to catch the various cases!
    #    If the user reads from a block that is in the file, but doesn't have
    #    a block allocated to it, just copy 0-bytes to the buffer for that block

    def read(self,buffer, file_offset: int):
        """
        Read from this INode into buffer

        :param file_offset: the offset into the file we want to read from
        :param buffer:      read up to len(buffer) bytes into this buffer
        :return:            number of bytes successfully read
        """
        startingOffset = file_offset
        offset = file_offset
        endOffset = startingOffset + len(buffer)
        bp = 0
        #print("reead~; length: " + str(self.length) + "." )
        while endOffset-offset != 0:
            #print("endOf: " + str(endOffset) + " ; offset: " + str(offset))
            blockIndex = offset // self.masterBlock.blockSize
            readIndex = blockIndex*self.masterBlock.blockSize
            startWriteAt = 0
            restOfBlock = self.masterBlock.blockSize
            if readIndex < startingOffset:
                startWriteAt = startingOffset-readIndex
            if (readIndex + self.masterBlock.blockSize) > endOffset:
                restOfBlock = endOffset - readIndex
            dataBlockAddr = self.getDiskAddrOfBlock(blockIndex, False)
            dataBlock = self.parentFS.retrieveBlock(dataBlockAddr)
            for i in range(restOfBlock-startWriteAt):
                buffer[bp*self.masterBlock.blockSize + i] = dataBlock[startWriteAt + i]
            #print("pre-cache")
            self.parentFS.cacheBlock(dataBlockAddr,dataBlock)
            offset = offset + (restOfBlock-startWriteAt)
            bp += 1

        #print("Reading from inode: " + str(self.inodeNum) + " with msg: " + str(buffer.decode("utf-8")) + " |||")

    # TODO: Assignment 3.2
    #     Similarly tricky as read, except when you look up blocks, pass the
    #     alloc = True flag to getDiskAddrOfBlock, so that the block does get
    #     allocated.
    def write(self, buffer, file_offset: int):
        """
        Write buffer to INode @ file_offset

        :param file_offset:  offset we want to write to
        :param buffer:       write these bytes to the file
        :return:             number of bytes written
        """
        #print("Writing to inode: " + str(self.inodeNum) + " with msg: " + str(buffer.decode("utf-8")) + " |||")
        startingOffset = file_offset
        offset = file_offset
        endOffset = startingOffset + len(buffer)
        bp = 0

        while endOffset-offset != 0:
            blockIndex = offset // self.masterBlock.blockSize
            readIndex = blockIndex*self.masterBlock.blockSize
            startWriteAt = 0
            restOfBlock = self.masterBlock.blockSize
            if readIndex < startingOffset:
                startWriteAt = startingOffset-readIndex
            if (readIndex + self.masterBlock.blockSize) > endOffset:
                restOfBlock = endOffset - readIndex
            dataBlockAddr = self.getDiskAddrOfBlock(blockIndex, True)
            dataBlock = self.parentFS.retrieveBlock(dataBlockAddr)
            for i in range(restOfBlock-startWriteAt):
                dataBlock[startWriteAt + i] = buffer[bp*self.masterBlock.blockSize + i]
            self.parentFS.cacheBlock(dataBlockAddr,dataBlock)
            offset = offset + (restOfBlock-startWriteAt)
            bp += 1

        pass

    # isFile and isDirectory help clients of the API not need to know about
    # our enum type.

    # create an array of block pointers from a data block (assumes data block is meant to be block of pointers)
    def writeBlockOfPtrs(self,blockNum,ptrsToPack):
        blockOfPtrs = bytearray(0)
        for x in range(0,self.ptrsPerBlock):
            blockOfPtrs.extend(struct.pack("=i", ptrsToPack[x]))
        #print("writing block of pointers at: " + str(blockNum))
        self.parentFS.cacheBlock(blockNum,blockOfPtrs)
        return

    def blockToBlockPtrs(self,blockOfPtrs):
        retPtrArray = [0] * self.ptrsPerBlock
        for x in range(0,self.ptrsPerBlock):
            (retPtrArray[x],) = struct.unpack("=i", blockOfPtrs[4*x:4*x+4])
        return retPtrArray

    def isFile(self):
        return self.flags == INodeType.FILE

    def isDirectory(self):
        return self.flags == INodeType.DIRECTORY

    # returns a character with the textual representation of its type
    def charRep(self):
        chars = "_fds"
        return chars[self.flags.value]

    def truncate(self, len):
        # TODO  Perserve existing block pointers when inode length increased
        # TODO: mark any allocated blocks in the truncated range
        #       as free if we shorten the inode
        #print("truncating")
        self.length = len

    ########### Internal functions

    def getDiskAddrOfBlock(self, block_number, alloc=False):
        """
        Get the disk address of <block_number> in this INode
            just a wrapper for the _recursive version below
        :param block_number:    the block we're looking for
        :param alloc:           if it's not there, do we allocate one?
        :return:                -1 on failure, or a > 0 block_number for this INode's block
        """
        if block_number*self.masterBlock.blockSize > self.length:
            print("Error: getDiskAddrOfBlock: read past size of inode")
            return -1
        return self.getDiskAddrOfBlock_recursive(block_number, alloc, self.blockPtrs, self.level,0)

    # TODO: Assignment 3.1
    #     Start by considering just level 0 (the blocks array is an array of block addresses)
    #     Then figure what size is too big for level 0, and how to convert to a level-1 inode,
    #     and how to look up data in a level 1 inode, then use recursion to take care of bigger levels

    def getDiskAddrOfBlock_recursive(self, blockNumber, alloc, blocks, level, blocksBlockPtr):
        """
        Helper function for getDiskAddrOfBlock, which takes level and blocks, which makes recursion feasible
        In a lot of ways, this is the real business of an INode.
        Note, if the INode grows, we may have to increase the level.

        :param block_number: the block we seek
        :param alloc:        whether we should allocate if the sought block is missing
        :param blocks:       the block array at this level
        :param level:        the distance from the leaves of the block pointer tree
        :return:             -1 if alloc is false and block is missing, otherwise the disk block address
                                corresponding to this INode's data @ block_number
        """

        # base case, return or allocate block, reject if inode currently too small
        if level == 0:
            if len(blocks) <= blockNumber:
               print("Error: getDiskAddrOfBlock: attempted access beyond inode size")
               return -1
            if blocks[blockNumber] == 0:
                blocks[blockNumber] = self.parentFS.allocBlock()
                if (blocksBlockPtr == 0):
                    self.blockPtrs = blocks  # top level inode blocks
                else:
                    self.writeBlockOfPtrs(blocksBlockPtr,blocks)
                return blocks[blockNumber]
            return blocks[blockNumber]

        ptrsPerPtr = self.ptrsPerBlock**level
        newBlockIndex = blockNumber//ptrsPerPtr
        newBlockNumber = blockNumber-(newBlockIndex*ptrsPerPtr)

        if len(blocks) <= newBlockIndex:
            print("Error: getDiskAddrOfBlock: attempted access beyond inode size")
            return -1

        newBlocks = None

        if(blocks[newBlockIndex] == 0): #if no block pointer, allocate block
            blocks[newBlockIndex] = self.parentFS.allocBlock()
            #update blocks since is given a new blockptr
            if(blocksBlockPtr == 0):
                self.blockPtrs = blocks #top level inode blocks
            else:
                self.writeBlockOfPtrs(blocksBlockPtr,blocks)
            newBlocks = [0]*self.ptrsPerBlock
            self.writeBlockOfPtrs(blocks[newBlockIndex],newBlocks)
        else:
            newBlocks = self.blockToBlockPtrs(self.parentFS.retrieveBlock(blocks[newBlockIndex],True))
        return self.getDiskAddrOfBlock_recursive(newBlockNumber,alloc,newBlocks,level-1,blocks[newBlockIndex])

        pass

    def pack(self, blockDev, blockNum):
        """
        we store all 28 inode block pointers with a for loop
        """
        inodeBytes = bytearray(struct.pack("=hiibhbii",
                                           self.inodeNum,
                                           self.cdate,
                                           self.mdate,
                                           self.flags.value,
                                           self.perms,
                                           self.level,
                                           self.length,
                                           self.magicNumber))

        for x in range(26):
            inodeBytes.extend(struct.pack("=i", self.blockPtrs[x]))
        blockDev.write_block(blockNum, inodeBytes, True)

    def unpack(self, blockDev, blockNum):
        """
        on unpack (as part of unmount) we must update our masterblock reference and inital blockmap size

        we load all 28 inode block pointers with a for loop
        """
        self.masterBlock = self.parentFS.masterBlock
        self.ptrsPerBlock = self.masterBlock.blockSize // 4
        inodeBytes = bytearray(self.masterBlock.blockSize)
        blockDev.read_block(blockNum, inodeBytes)

        (self.inodeNum,
         self.cdate,
         self.mdate,
         flagVal,
         self.perms,
         self.level,
         self.length,
         self.magicNumber) = struct.unpack("=hiibhbii", inodeBytes[:22])

        self.flags = INodeType(flagVal)

        for x in range(26):
            (self.blockPtrs[x],) = struct.unpack("=i", inodeBytes[22 + x * 4:22 + (x + 1) * 4:])