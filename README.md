# opSysHW4

## Run NoseTests with nosetests FileSystem.py

### INode.read & Inode.write:
-start of read/write: read block from calculated starting index, to end of block

-body of read/write: read from start to end of block

-end of read/write: fread from start of block to calculated end index.
