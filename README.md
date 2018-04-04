# opSysHW4^(tm): Now with Shell history!

## Availble Functionality (commands you can enter):

exit, quit............................................................................close shell
ls [directoy/path]..............................show files/dirs in current dir [or specified dir]
cat <filename>.....................................................read out full contents of file
write <filename> <message>.....................................write into file from start of file
write_at <filename> <offset> <message>................................write into file from offset
mkdir <dirName>.........................................................create dir in current dir
cd <filename>...............................................................move to specified dir
echo [text].............................................................................echo text
newfs <filename> <block count> [blocksize]...................................create a file system
blockmap..................................................................print state of blockmap
alloc_block...............................................................reserve a block for use
free_block <block number>..............................................free a block's reservation
inode_map.................................................................print state of inodemap
alloc_inode <inode type id>.......................................allocate inode of specific type
free_inode <inode number>...........................................free an inode's reserveration


## Run NoseTests with nosetests FileSystem.py

### INode.read & Inode.write:
-start of read/write: read block from calculated starting index, to end of block

-body of read/write: read from start to end of block

-end of read/write: read from start of block to calculated end index.
