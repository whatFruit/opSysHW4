import sys
import os
import fileinput
import readline
import rlcompleter
import FileSystem

histFileName = "shell_hist.txt"

class Shell:
    """ Simple Python shell """


def repl():
    prompt = '> '
    cmd = ''
    line = None
    fileSys = None
    while True:

        # implemented new loop structure from dylan's As.3 starting point
        try:
            line = input(prompt)
        except EOFError:
            break;

        words = line.split()
        numWords = len(words)
        if len(words) == 0:
            pass
        elif words[0] in ('exit', 'quit'):
            break
        elif words[0] in ('ls', 'dir'):
            if numWords > 2:
                print("Error: ls - requires one or zero arguments: 'ls [directoy/path]'")
            elif fileSys is None:
                print("Error: ls - a fileSys must be mounted first '")
            elif numWords == 1:
                fileSys.printDir()
            else:
                fileSys.printDir(words[1])
        elif words[0] == 'cat':
            if numWords != 2:
                print("Error: cat - requires one argument: 'cat <filename>'")
            elif fileSys is None:
                print("Error: cat - a fileSys must be mounted first '")
            else:
                fileSys.printFile(words[1])
        elif words[0] == 'write':
            if numWords != 3 or  numWords != 4:
                print("Error: write - requires two arguments: 'write <filename> <message> (offset)'")
            elif fileSys is None:
                print("Error: write - a fileSys must be mounted first '")
            elif numWords == 3:
                fileSys.writeFile(words[1],words[2],-1)
            else:
                fileSys.writeFile(words[1], words[2],words[3])
        elif words[0] == 'mkdir':
            if numWords != 2:
                print("Error: mkdir - requires one argument: 'mkdir <dirName>'")
            elif fileSys is None:
                print("Error: mkdir - a fileSys must be mounted first '")
            else:
                fileSys.makeDir(words[1])
        elif words[0] == 'touch':
            if numWords != 2:
                print("Error: touch - requires one argument: 'cd <filename>'")
            elif fileSys is None:
                print("Error: touch - a fileSys must be mounted first '")
            else:
                fileSys.makeFile(words[1])
        elif words[0] == 'cd':
            if numWords != 2:
                print("Error: cd - requires one argument: 'cd <path>'")
            elif fileSys is None:
                print("Error: cd - a fileSys must be mounted first '")
            else:
                fileSys.moveCurrDir(words[1])
        elif words[0] == 'echo':
            print(*words[1:]," ")
        elif words[0] == 'newfs':
            # Creates a file system given the correct arguments, error msg otherwise
            if numWords < 3 or numWords > 4:
                print("Error: newfs - requires two arguments: 'newfs <filename> <block count> [optinal blocksize]'")
            elif numWords == 4:
                FileSystem.FileSystem.createFileSystem(words[1], int(words[2]), int(words[3]))
            else:
                FileSystem.FileSystem.createFileSystem(words[1], int(words[2]))
        elif words[0] == 'mount':
            # Mounts filesystem from current directory, reference stored in fileSys
            if numWords != 2:
                print("Error: mount - requires one argument: 'mount <filename>'")
            elif fileSys is not None:
                print("Error: mount - fileSys already mounted, please unmount'")
            else:
                fileSys = FileSystem.FileSystem.mount(words[1])

        elif words[0] == 'blockmap':
            # display block map availbility
            if numWords != 1:
                print("Error: blockmap - requires no arguments'")
            elif fileSys is None:
                print("Error: blockmap - no file system mounted'")
            else:
                fileSys.printBlockMap()

        elif words[0] == 'alloc_block':
            # allocates first open block in block map (0 -> 1)
            if numWords != 1:
                print("Error: alloc_block - requires no arguments'")
            elif fileSys is None:
                print("Error: alloc_block - no file system mounted'")
            else:
                fileSys.allocBlock()

        elif words[0] == 'free_block':
            # frees specified block (1||0 -> 0)
            if numWords != 2:
                print("Error: free_block - requires one argument, 'free_block <n>'")
            elif fileSys is None:
                print("Error: free_block - no file system mounted'")
            else:
                fileSys.freeBlock(int(words[1]))

        elif words[0] == 'inode_map':
            # displays map of inode states, similar to block map
            if numWords != 1:
                print("Error: inode_map - requires no arguments'")
            elif fileSys is None:
                print("Error: inode_map - no file system mounted'")
            else:
                fileSys.printINodeMap()

        elif words[0] == 'alloc_inode':
            # allocates first availble inode in inode map according to type
            if numWords != 2:
                print("Error: alloc_inode - requires one argument, 'alloc_inode <type>'")
            elif fileSys is None:
                print("Error: alloc_inode - no file system mounted'")
            else:
                fileSys.allocINode(words[1])

        elif words[0] == 'free_inode':
            # sets specifided inode to 'O'
            if numWords != 2:
                print("Error: free_inode - requires one argument, 'free_inode <n>'")
            elif fileSys is None:
                print("Error: free_inode - no file system mounted'")
            else:
                fileSys.freeINode(int(words[1]))

        elif words[0] == 'unmount':
            # flush values to disk and set fileSys to None
            if numWords != 1:
                print("Error: unmount - requires no arguments'")
            elif fileSys is None:
                print("Error: unmount - no file system mounted'")
            else:
                fileSys.unmount()
                fileSys = None

        else:
            print("unknown command {}".format(words[0]))

    # all done, clean exit
    print("bye!")
    readline.write_history_file(histFileName)


assert sys.version_info >= (3, 0), "This program requires Python 3"

if __name__ == '__main__':
    try:
        readline.read_history_file(histFileName)
    except FileNotFoundError:
        open(histFileName, "wb").close()

    readline.parse_and_bind("tab: complete")
    repl()
