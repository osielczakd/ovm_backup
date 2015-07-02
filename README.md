# ovm_backup
A script to take backups of Oracle VM virtual machines

Usage:

  backup_ovm_vm.py -v <VM_Name> [OPTION] [-f] [--debug]
  
	Where OPTION is one or more of:
	
	-c | --compress						Compress backup
	
	-d | --dest-dir						destination directory for the backup . This option implies compression (due to data size).
	
	-f | --forceshutdown					force shutdown of VM
	
	-i | --manager-key					OVM Manager ssh login private key
	
	-I | --server-key					OVM Server ssh login private key
	
	-l									log directory
	
	-m | --managerhost					OVM Manager hostname/IP
	
	-o | --online						VM online backup
	
	-p | --port							OVM Manager port
	
	-u | --username						OVM Manager username
	
	--debug								print verbose output of commands
