#!/usr/bin/python
"""
     $Id: backup_vm.py 983 2013-10-03 16:40:58Z tbr $

  This script copies a virtual machine to a Serverpool.
  As long as the target is the same Repository like the source the 'clone vm'  
  in sshcli is much easier to use!
  The script creates a new virtual machine with same configuration as the 
  source. 

  Parameters:

  Restrictions:
     - no spaces in parameters allowed

  Where can I find pexpect?
  http://pexpect.sourceforge.net/pexpect.html
  
  Temporairly we also use sshpass to skip the whole expect/pexpect complications by logging in --> http://sourceforge.net/projects/sshpass/
"""

#import pexpect, getpass
import pexpect, getpass, subprocess
import sys, getopt, os, datetime, logging, traceback, tarfile
import re, time
import ConfigParser

import xml.etree.ElementTree as ElementTree

# globale Variables
argdictionary = {}


class Logger():
    """
    """
    def __init__(self, logPath = '', fileName = '', logLevel = logging.INFO):
        """
        we use different formats for logging to file and console!
        """
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s")
        logFormatter2 = logging.Formatter("%(message)s")

        if logPath == '' or fileName == '':
            self.fileLogging = 'no'
        else:
            self.fileLogging = 'yes'

        try:
            logfile = str(logPath) + '/' + str(fileName) + '.log'
            fileHandler = logging.FileHandler(logfile.format(logPath, fileName))
        except:
            print 'Unable to create logfile (%s). Aborting script!', logfile
            type_, value_, traceback_ = sys.exc_info()
            ex = traceback.format_exception(type_, value_, traceback_)
            print ex[-1].strip('\n')
            sys.exit(2)

        fileHandler.setFormatter(logFormatter)

        consoleHandler = logging.StreamHandler()

        consoleHandler.setFormatter(logFormatter2)

        self.__rootLogger = logging.getLogger()
        self.__rootLogger.addHandler(fileHandler)
        self.__rootLogger.addHandler(consoleHandler)

        self.setLogLevel(logLevel)
        logging.info('Start logging')

    def setLogLevel(self, LogLevel):
        self.__rootLogger.setLevel(LogLevel)


class OVMcli:

    def __init__(self):
        self.__child = ''
        self.__dataListvm = []
        self.__dataListVNIC = []
        self.__dataListvmDisk = []

        self.OVMsshcliok = 'OVM>'
        self.sshclitimeout = 10

        # Public Dictionary for VM-Information
        self.dataListVM = {}
        # Public Lists for Disks and VNICs
        self.dataListDisk = []
        self.dataListVNIC = []


    def login(self, argdictionary):
        if not argdictionary['managerhost']:
		logging.critical("login: Hostname empty!")
            	sys.exit(1)
	# make sure host is reachable
	response = os.system('nc -v -z ' + argdictionary['managerhost'] + ' ' + str(argdictionary['port']))
	if response != 0:
		logging.critical("SSH: Host not reachable! " + argdictionary['managerhost'])
            	sys.exit(1)
	logging.info('SSHCLI login to ' + argdictionary['managerhost'])
	if not argdictionary['mpassword']:
		self.__child = pexpect.spawn('ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=40 -o UserKnownHostsFile=/dev/null -p ' + str(argdictionary['port']) + ' ' + '-i' + ' ' + argdictionary['manager-key'] + ' ' + argdictionary['username'] + '@' + argdictionary['managerhost'], timeout= self.sshclitimeout)
	else:
		self.__child = pexpect.spawn('sshpass -p ' + argdictionary['mpassword'] + ' ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=40 -o UserKnownHostsFile=/dev/null -p ' + str(argdictionary['port']) + ' ' + argdictionary['username'] + '@' + argdictionary['managerhost'], timeout= self.sshclitimeout)
	self.__state = self.__child.expect([pexpect.TIMEOUT, self.OVMsshcliok])
	if self.__state == 0:
		logging.critical('Fehler beim Login!')
		logging.critical('ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p ' \
				  + str(argdictionary['port']) + ' ' + argdictionary['username'] + '@' + argdictionary['managerhost'])
		sys.exit (1)
	self.cliSetoutputMode('XML')


    def logout(self):
        logging.info('SSHCLI logout')
        self.__child.close


    def stopvm(self):
        if self.getvmState() != 'Started':
            for item in self.__dataListvm:
                if item[0] == 'Name':
                    logging.info("SSHCLI  stop VM " + item[1])
                    self.__cliSendCmd('stop vm name=' + item[1])


    def startvm(self):
        if self.getvmState() == 'Stopped':
            for item in self.__dataListvm:
                if item[0] == 'Name':
                    logging.info( "SSHCLI start VM " + item[1])
                    self.__cliSendCmd('start vm name=' + item[1])


    def getvmState(self):
        """
        Get the state of VM from last 'show vm name ...'
        """
        return self.dataListVM.get('Status', 'Unknown')[0]


    def getovmSever4VM(self):

        ovmserver =  self.dataListVM.get('Server', 'not defined')[1]
        if ovmserver == 'not defined':
            logging.critical('getovmSever4VM: ' + str(  self.dataListVM))

        logging.debug('getovmSever4VM: ' + ovmserver)
	print 'OVM Server is: '.format(ovmserver)
        return ovmserver


    def getvmVirtualDisks4VM(self):
        virtualDiskList = []
        #prinz self.__dataListvmDisk
        try:
            self.__dataListvmDisk[0]
        except IndexError:
            # nicht vorhanden
            logging.warning('getvmVirtualDisks4VM: no virtual disks found for VM')
        dataListDisktmp = []
        for itemlist in self.__dataListvmDisk:
            for item1 in itemlist:
                # we need the 'virtual Disk' information
                if item1[0] == 'Virtual Disk':
                    # we get some details:
                    dataListtmp = []
                    for subItem1 in item1[1:]:
                        if subItem1[0] in ('Name', 'Id', 'Repository Id'):
                            dataListtmp.append(subItem1)
                    dataListDisktmp.append(dataListtmp)
                    virtualDiskList.append(dataListtmp)
        return virtualDiskList


    def printVMDetails(self):
        """print Details from internal data
        """
        pass
        print "VM-Details"
        for item in sorted(self.dataListVM.keys()):
            linestr = item.ljust(24) + str(self.dataListVM[item])
            logging.info(linestr)
        print ""
        print ""
        print "Network-Inferfaces for VM"
        for itemlist in self.dataListVNIC:
            print "#################################################################"
            for item in sorted(itemlist.keys()):
                linestr = item.ljust(24) + str(itemlist[item])
                logging.info(linestr)
        print ""
        print ""
        print "Disk-Details for VM"
        for itemlist in self.dataListDisk:
            print ""
            print "################## Virtual Disk Mapping ########################"
            # print Data for virtualDiskMapping
            for line in sorted(itemlist.keys()):
                if line[0:4] == 'VDM_':
                    linestr = line[4:].ljust(24) + str(itemlist[line])
                    logging.info(linestr)
            print "################### Virtual Disk #####"
            for line in sorted(itemlist.keys()):
                if line[0:3] == 'VD_':
                    linestr = line[3:].ljust(24) + str(itemlist[line])
                    logging.info(linestr)


    def getDataVM(self,VMname):
        dataListvmDiskMapping = []
        dataListtmp = []

        self.__cliShowItem('vm', 'name', VMname)
        XMLdata = self.__getDataFromCLI()
        self.__dataListvm = self.__splitXML(XMLdata, 'ShowCommandResult')
        # we need to search __dataListvm for the details of VNIC, vmDiskMapping ...
        for item in self.__dataListvm:

            self.dataListVM[item[0]] = item[1:]

            if re.search('^Vnic ', item[0]):
                # we found a VNIC
                # => get the data for the VNIC
                self.__cliShowItem('VNIC', 'id', item[1])
                XMLdata = self.__getDataFromCLI()
                dataListtmp = (self.__splitXML(XMLdata, 'ShowCommandResult'))
                self.__dataListVNIC.append(dataListtmp)

            elif re.search('^VmDiskMapping ', item[0]):
                # we found a vmDiskMapping
                # => get the data for the Mapping
                self.__cliShowItem('vmDiskMapping', 'id', item[1])
                XMLdata = self.__getDataFromCLI()
                dataListtmp = (self.__splitXML(XMLdata, 'ShowCommandResult'))
                # wee need to search over all mappings to get the details for virtualdisk, cdrom or physical disk
                dataListtmp.insert(0, 'VM Disk Mapping')
                dataListvmDiskMapping.append(dataListtmp)

                # Insert information in new variables for leter use
                # Refactoring of source will only use this variables in the future.
                # => using dictionary with list for easier getting data foe Disks
                detaildict = {}
                for item in dataListtmp[1:]:
                    detaildict['VDM_' + str(item[0])] = item[1:]
                self.dataListDisk.append(detaildict)
                logging.debug(detaildict)

        # fill new structure for VNICs
        for itemVNIC in self.__dataListVNIC:
            VNICdict = {}
            for item in itemVNIC:
                VNICdict[item[0]] = item[1:]
            self.dataListVNIC.append(VNICdict)

        # Wee need to search over all dataListvmDiskMapping
        for itemvmDiskMap in dataListvmDiskMapping:

            dataListtmp = []
            for item in itemvmDiskMap:
                if item[0] == 'Virtual Disk Id':
                    # we search for Disk Details
                    # ID *.img$   => virtualDisc
                    # ID *.iso$   => CDROM
                    # ID * 'else' => PhysicalDisc
                    if item[0] == 'EMPTY_CDROM':
                        # nothing to get for this type
                        pass
                    elif re.search('.img$', item[1]):
                        self.__cliShowItem('virtualDisk', 'id', item[1])
                        XMLdata = self.__getDataFromCLI()
                        dataListtmp = (self.__splitXML(XMLdata, 'ShowCommandResult'))
                        dataListtmp.insert(0,'Virtual Disk')
                    elif re.search('.iso$', item[1]):
                        self.__cliShowItem('virtualcdrom', 'id', item[1])
                        XMLdata = self.__getDataFromCLI()
                        dataListtmp = (self.__splitXML(XMLdata, 'ShowCommandResult'))
                        dataListtmp.insert(0,'Virtual CDROM')
                    else:
                        self.__cliShowItem('physicalDisk', 'id', item[1])
                        XMLdata = self.__getDataFromCLI()
                        dataListtmp = (self.__splitXML(XMLdata, 'ShowCommandResult'))
                        logging.warning('unknown type for virtual disk Mapping ' + str(itemvmDiskMap))
                        dataListtmp.insert(0,'Unknown Type')
#						dataListDiskDetail = _subsshcli(child, 'show virtualdisk id=' + item[1])

            # re add the entry to the global list __dataListvmDisk
            # The list has 2 entry per vmDiskMapping:
            # 1st vmDiskMapping
            # 2nd virtualDisk|physicalDisk ...
            tmplist = []
            tmplist.append(itemvmDiskMap )
            tmplist.append(dataListtmp)
            self.__dataListvmDisk.append(tmplist)

            #
            # we fill the new structure dataListDisk!
            #
            VD_Id = ''
            # get the Id for Virtual Disk
            for item in  dataListtmp[1:]:
                if item[0] == 'Id':
                    VD_Id =  item[1]

            # We search the VD_Id in self.dataListDisk for adding the details to dictionary
            # we need the position in the list for adding the data
            for i, dic in enumerate(self.dataListDisk):
                if dic['VDM_Virtual Disk Id'][0] == VD_Id:
                    dataListDiskPointer = i

            # we could add the data to datdataListDisk
            for item in  dataListtmp[1:]:
                self.dataListDisk[dataListDiskPointer]['VD_' + str(item[0])] = item[1:]


    def cliSetoutputMode(self, outmode='XML'):
        """Set outputmode to XML for safe formated resultdata from ovmcli
        """
        self.__child.sendline('set outputMode=' + outmode + '\r')
        i = self.__child.expect([pexpect.TIMEOUT,self.OVMsshcliok])
        if i == 0:
            logging.critical('outputMode could not be set. Aborting script!')
            sys.exit (1)


    def __cliSendCmd(self, cmdline):
        self.__child.sendline(cmdline + '	\r')
        i = self.__child.expect([pexpect.TIMEOUT,self.OVMsshcliok])
        if i == 0:
            logging.critical('cliSendCmd: ' + cmdline)
            sys.exit (1)


    def __cliShowItem(self, itemtype, itemname, itemvalue):
        cmdline = 'show ' + itemtype + ' ' + itemname + '=' + itemvalue
        self.__cliSendCmd(cmdline)


    def __getDataFromCLI(self):
        sshcliout =  self.__child.before
        # we only need the real XML-Data. Remove other stuff from output
        sshclioutXML = sshcliout[sshcliout.find('<?xml version="'):]
        return sshclioutXML


    def __splitXML(self, XMLdata, ParamSplitElement, ParamElementName='PropertyName', ParamElementValue='PropertyValue'):
        """ ParamSplitElement == ListCommandResult | ShowCommandResult
        This function creates a Python-list from given XMLdata
        """
        def _appenddataList(dataList, elemPropertyName, elemPropertyValue):
            """ Split data from dataList. The XML-Result from OVM has a special format
            PropertyValue could hould an id and the value for name
            => The name-value is inside the []"""
            if elemPropertyValue.find("[") > 0:
                # the elemPropertyValue must be split in 2 entries!
                itemvalue1 = elemPropertyValue[:elemPropertyValue.find("[")-2]
                itemvalue2 = elemPropertyValue[elemPropertyValue.find("[")+1:elemPropertyValue.find("]")]
                dataList.append([elemPropertyName, itemvalue1, itemvalue2])
            else:
                dataList.append([elemPropertyName, elemPropertyValue])
            return dataList
            None

        dataList = []
        ETroot = ElementTree.fromstring(XMLdata)
        elemPropertyName = ''
        elemPropertyValue = ''
        for elem in ETroot.findall('.//*'):
            if re.search(ParamSplitElement, elem.tag):
                # Did we found a new item?
                # => yes, append list with old data
                if elemPropertyName != '':
                    dataList = _appenddataList(dataList, elemPropertyName, elemPropertyValue)
                # found a new Item
                elemPropertyName = ''
                elemPropertyValue = ''
            else:
                if elem.tag == ParamElementName:
                    elemPropertyName = elem.text
                elif elem.tag == ParamElementValue:
                    elemPropertyValue = elem.text

        if elemPropertyName != '':
            dataList = _appenddataList(dataList, elemPropertyName, elemPropertyValue)

        return dataList


    def writeConfiguration(self, configFile):
        """
        Creates a file with the configuration of this virtual machine. The format is created with ConfigParser.
        We create a configugration item for this VM for later use when recreating the vm from the configuration
        The data is read from new variables so there is no need for refactoring at later time.
        """
        MainSection = 'VM'
        cfgfile = open(configFile, 'w')
        logging.info('create configfile: ' + configFile)
        Config = ConfigParser.ConfigParser()

        # create configuration for VM
        Config.add_section(MainSection)
        for item in self.dataListVM.keys():
            Config.set(MainSection, item, self.dataListVM[item])

        # create configuration for VNIC
        # we search for VNICs in VM configuration
        for keyvalue in self.dataListVM.keys():
            if keyvalue[0:5] == 'Vnic ':
                # create the configuration
                Config.add_section(keyvalue)
                # Search the VNIC in dataListVNIC
                for item in self.dataListVNIC:
                    if item['Id'][0] == self.dataListVM[keyvalue][0]:
                        for line in item:
                            Config.set(keyvalue, line, item[line])

            elif keyvalue[0:14] == 'VmDiskMapping ':
                # create the configuration
                Config.add_section(keyvalue)
                # Search the virtualdiskMapping in dataListDisk
                for item in self.dataListDisk:
                    if item['VDM_Id'][0] == self.dataListVM[keyvalue][0]:
                        for line in item:
                            Config.set(keyvalue, line, item[line])

        Config.write(cfgfile)
        cfgfile.close()


class OVMSssh:

    def __init__(self, logfile = ''):
        __sshhandle = ""
        __stdoutdefaulthandle = ''
        BackupDateTime = ''
        BackupDateTimestr = ''
        OVSRepoSnapshotSubDir = ''
        SnapshotDirname = ''
        PROMPT_SET_SH = "PS1='-PEXPECT-# '"
        COMMAND_PROMPT = 'root'
        self.__stdoutdefaulthandleold = sys.stdout
        self.OVSRepoSnapshotSubDir = 'snapshot_backup'
        self.BackupDateTime = datetime.datetime.today
        self.BackupDateTimestr = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        self.PROMPT_SET_SH = "PS1='-PEXPECT-\$ '"
        self.COMMAND_PROMPT = '-PEXPECT-'
        self.expectlogfile = logfile


    def login(self,sshhostname):
        # Try to ping the host
        if not sshhostname:
                logging.critical("login: Hostname empty!")
                sys.exit(1)
        else:
            response = os.system("ping -c 1 " + sshhostname + ' > /dev/null')
            if response != 0:
                logging.critical("SSH: Host not reachable! " + sshhostname)
                sys.exit(1)
	    if not argdictionary['spassword']:
		cmdstr = 'ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=40 root@' + sshhostname + ' -i ' + argdictionary['server-key']
		self.__sshhandle = pexpect.spawn(cmdstr + '\r', timeout= 10)
	    else:
		cmdstr = 'ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=40 root@' + sshhostname
		self.__sshhandle = pexpect.spawn('sshpass -p ' + argdictionary['spassword'] + ' ' + cmdstr + '\r', timeout= 10)
            # we log everything on ssh to a logfile when parameter is not empty
            if self.expectlogfile != '' :
                fout = file(self.expectlogfile, 'w')
                self.__sshhandle.logfile = fout

            self.__sshhandle.expect('root')
            self.__sshhandle.setecho(False)
            self.__sshhandle.setwinsize(30, 300)

            # Set new Prompt for all commands
            self.__sshhandle.sendline(self.PROMPT_SET_SH)
            self.__sshhandle.expect(self.COMMAND_PROMPT)
            self.cmdsend('export TERM=vt52', 2)
            # force exit of shell when command has exitcode != 0
            self.cmdsend('set -e', 2)


    def logout(self):
        logging.info('SSH: logout')
        self.__sshhandle.logout


    def __createBackupdir(self, SnapshotDirname):
        # create the destination-Directory for Snapshots
        # 1st check for an existing directory!
        logging.debug('__createBackupdir: check Snapshotdirectory ' + SnapshotDirname)
        print "Check for existing Snapshotdirectory " + SnapshotDirname
        print "Creating Snapshot-Directory " + SnapshotDirname
        sshcmd = 'mkdir -p ' + SnapshotDirname
        try:
            self.cmdsend(sshcmd,2)
        except:
            logging.critical('createBackupdir: Error while creating the directory :' + SnapshotDirname)
            raise


    def __stdouttonull(self):
        pass


    def __stdouttonulfile(self, stdoutfilename):
        f = open(stdoutfilename, 'w')
        sys.stdout = f


    def __stdouttonormal(self):
        sys.stdout = self.__stdoutdefaulthandleold


    def createmd5sum(self, srcfile):
        self.__stdouttonormal()

        sshcmd = 'md5sum -b ' + srcfile
        logging.info(sshcmd)
        self.cmdsend(sshcmd, 1800)

        # Get result from md5sum
        result = self.__sshhandle.before
        resultlist = []
        resultlist = result.split()

        # search for md5sum in list
        # index + 2 = checksum
        index = resultlist.index('md5sum')
        md5checksum = resultlist[index+3]
        logging.info('md5sum: ' + md5checksum + ' ' + srcfile)


    def __copyvmcfg(self, VMName, RepoID, DestDir):
        sshcmd = 'cp $(egrep -ir ' + VMName + ' /OVS/Repositories/' + str(RepoID) + '/VirtualMachines/ | cut -f1 -d":") ' + DestDir
	self.cmdsend(sshcmd,15)
		

    def checkfileocfs2(self, srcfile):
        self.__stdouttonull()
        sshcmd = 'df --type=ocfs2 -h ' + srcfile + ' | grep /OVS'
        self.cmdsend(sshcmd,5)
        return 'yes'


    def cmdsend(self, cmdline, timeout):
        try:
            expectprompt = [self.COMMAND_PROMPT]
            logging.debug('cmdsend: timeout ' + str(timeout) + ' command ' + cmdline)
            time.sleep(0.1)
            # adding returncode for checking the result of the command
            self.__sshhandle.sendline(cmdline)
            time.sleep(0.2)
            self.__sshhandle.expect(expectprompt, timeout = timeout)
            time.sleep(0.3)

            # a dummy return. otherwise there a strange problems while using pexpect with ssh...
            self.__sshhandle.sendline('')
            time.sleep(0.1)
            self.__sshhandle.expect(expectprompt, timeout = timeout)
            time.sleep(0.1)

#            print self.__sshhandle.before
            logging.debug('ende ' + cmdline)
            return 0
        except pexpect.TIMEOUT:
            # TIMEOUT results in an abort of all following statements
            # this is required due to the fact that a current running process could get the result for the next expect command
            # => we get a ok for next command from result of the command before. => we run out of sync with the commands!
            logging.critical('Timeout at : ' + cmdline)
            raise
        except pexpect.EOF:
            logging.critical( 'EOF at : ' + cmdline)
            raise





        a = self.__sshhandle.before
        self.__sshhandle.sendline(cmdline)
        logging.debug('cmdsend: ' + cmdline)
        time.sleep(0.5)
        try:
            self.__sshhandle.expect(self.COMMAND_PROMPT, timeout = cmdtimeout)
        except TIMEOUT:
            logging.warning('cmdsend: Timeout')
        except:
            logging.critical('cmdsend: ' + self.__sshhandle.before())


    def cmdresult(self):
        self.__result = self.__child.before
        logging.debug('cmdresult: ' + self.__result)
        return self.__result

    def __createreflink(self, srcfile, destfile):
        # 1 st Check the srcfile
        # => File must be on ocfs2-Filesystem for reflink
        if self.checkfileocfs2(srcfile) == 'no' :
            print "File not on OCFS2-Filesystem: " + srcfile
        else:
            cmdline = 'reflink -P --backup=off ' + srcfile + ' ' + destfile
            logging.info(cmdline)
            try:
                self.cmdsend(cmdline,10)
            except:
                raise
# REMOVED DUE TO LENGHTY TESTING, NEEDS TO BE RESTORED LATER:
#           self.createmd5sum(srcfile)
	
    def createSnapshotTarball(self, OVSSnapDir):
	tarballName = os.path.basename(OVSSnapDir) + '.tar.gz'
	tarballPath = os.path.dirname(OVSSnapDir) + '/' + tarballName
		
	print 'Creating backup tarball: ' + tarballPath
	logging.info("Creating tarball from VM backup " + tarballPath)
		
	cmdline = 'tar -cvzf ' + tarballPath + ' ' + OVSSnapDir
	try:
           self.cmdsend(cmdline,3600)
        except:
           raise

	print 'Tarball: ' + tarballPath + ' successfully created'
	logging.info("Successfully created " + tarballPath)
	return tarballPath
		

    def createSnapshot(self,vmname, virtualDiskList, virtualDiskMappingList, moveSnap):
        print " "
        print "##########"
        logging.info("Creating Snapshot for VM " + vmname + ' ' + datetime.datetime.today().strftime('%Y%m%d_%H%M'))
        for virtualDiskitem in virtualDiskList:
            DiskId = ''
            RepositoryId = ''
            DiskId = ''
            for virtualDiskDetail in virtualDiskitem:
                if virtualDiskDetail[0] == 'Id':
                    DiskId = virtualDiskDetail[1]
                if virtualDiskDetail[0] == 'Repository Id':
                    RepositoryId = virtualDiskDetail[1]
            logging.info('Disk-Id: ' + str(DiskId) + '  Repository: ' + RepositoryId)
            OVSdirname = '/OVS/Repositories/' + str(RepositoryId) + '/VirtualDisks/'
            OVSfilenameshort = str(DiskId)
            OVSfilename = OVSdirname  + '/' + OVSfilenameshort

            OVSdestdir = '/OVS/Repositories/' + str(RepositoryId) + '/' + self.OVSRepoSnapshotSubDir + '/' + vmname + '_' + self.BackupDateTimestr
            OVSdestfilename = OVSdestdir + '/' + OVSfilenameshort

            self.__createBackupdir(OVSdestdir)
            self.__createreflink(OVSfilename, OVSdestfilename)
	self.__copyvmcfg(vmname, RepositoryId, OVSdestdir)
			
	if moveSnap:
		TarFile = self.createSnapshotTarball(OVSdestdir)
		print 'Tarball is located at: ' + str(TarFile)
		return TarFile
	else:
		pass

    def transferSnapshot(self, argdictionary, sshhostname, RemoteFile):
	if not argdictionary['spassword']:
		syncCommand = 'rsync -avpz -e "ssh -i ' + argdictionary['server-key'] + '" ' + sshhostname + ':' + RemoteFile + ' ' + argdictionary['dest-dir']
		subprocess.check_call(syncCommand, shell=True)
		print 'Tarball successfully transfered from ' + RemoteFile + ' to ' + argdictionary['dest-dir']
	else:
		syncCommand = 'sshpass -p ' + argdictionary['spassword'] + ' rsync -avpz ' + sshhostname + ':' + RemoteFile + ' ' + argdictionary['dest-dir']
		subprocess.check_call(syncCommand, shell=True)
		print 'Tarball successfully transfered from ' + RemoteFile + ' to ' + argdictionary['dest-dir']

    def removeSnapshot(self, snapshotTarball, snapshotDirectory):
	cmdline = 'rm -rf ' + snapshotTarball + ' ' + snapshotDirectory
        logging.info(cmdline)
        try:
        	self.cmdsend(cmdline,60)
		print 'Snapshot directory ' + snapshotDirectory + ' and tarball ' + snapshotTarball + ' successfully removed'
        except:
                raise


def printusage():
	print "Usage:"
	print "%s -v <VM_Name> [OPTION] [-f] [--debug]" % argdictionary['scriptname']
	print "Where OPTION is one or more of:"
	print "-c | --compress						Compress backup (if not set defaults to: %s)" % argdictionary['compression']
	print "-d | --dest-dir						destination directory for the backup (if not set defaults to: %s). This option implies compression (due to data size)." % argdictionary['dest-dir']
	print "-f | --forceshutdown					force shutdown of VM (if not set defaults to: %s)" % argdictionary['forceshutdown']
	print "-i | --manager-key					OVM Manager ssh login private key (if not set defaults to: %s)" % argdictionary['manager-key']
	print "-I | --server-key					OVM Server ssh login private key (if not set defaults to: %s)" % argdictionary['server-key']
	print "-l									log directory (if not set defaults to: %s)" % argdictionary['logdir']
	print "-m | --managerhost					OVM Manager hostname/IP (if not set defaults to: %s)" % argdictionary['managerhost']
	print "-o | --online						VM online backup (if not set defaults to: %s)" % argdictionary['online']
	print "-p | --port							OVM Manager port (if not set defaults to: %s)" % str(argdictionary['port'])
	print "-u | --username						OVM Manager username (if not set defaults to: %s)" % argdictionary['username']
	print "--debug								print verbose output of commands (if not set defaults to: %s)" % argdictionary['debug']

def getparameter(argv):

    scriptname = argv[0]
    arglist = argv[1:]

    global argdictionary
	
    argdictionary['scriptname'] = argv[0]
    argdictionary['managerhost'] = 'localhost'
    argdictionary['online'] = 'yes'
    argdictionary['port'] = 10000
    argdictionary['forceshutdown'] = 'no'
    argdictionary['username'] = 'admin'
    argdictionary['mpassword'] = ''
    argdictionary['spassword'] = ''
    argdictionary['vmname'] = ''
    argdictionary['logdir'] = os.getcwd()
    argdictionary['debug'] = 'no'
    argdictionary['manager-key'] = os.getcwd() + '/.ssh/admin_rsa'
    argdictionary['server-key'] = ''#os.getcwd() + '/.ssh/ovsroot_rsa'
    argdictionary['dest-dir'] = ''
    argdictionary['compression'] = False



    try:
        opts, args = getopt.getopt(arglist,"?ofm:s:c:u:d:v:i:I:l:V:p:r:R:",["managerhost","debug","serverpool","compress","dest-dir","username","manager-key","server-key","repository","repositorytarget","vmname","port","vmnamenew"])
    except getopt.GetoptError:
        printusage
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-?':
            print helpline
            sys.exit()
	elif opt in ("-c", "--compress"):
	    argdictionary['compression'] = True
	elif opt in ("-d", "--dest-dir"):
	    argdictionary['dest-dir'] = arg
	    argdictionary['compression'] = True
        elif opt in ("-f", "--forceshutdown"):
            # do the snapshot while VM is currently running
            argdictionary['forceshutdown'] = 'yes'
        elif opt in ("-i", "--manager-key"):
            argdictionary['manager-key'] = arg
	elif opt in ("-I", "--server-key"):
            argdictionary['server-key'] = arg
        elif opt in ("-l"):
            argdictionary['logdir'] = arg
        elif opt in ("-m", "--managerhost"):
            argdictionary['managerhost'] = arg
        elif opt in ("-o", "--online"):
            # do the snapshot while VM is currently running
            argdictionary['online'] = 'yes'
        elif opt in ("-p", "--port"):
            argdictionary['port'] = arg
        elif opt in ("-v", "--vmname"):
	    argdictionary['vmname'] = arg
        elif opt in ("-u", "--username"):
            argdictionary['username'] = arg
        elif opt in ("--debug"):
            argdictionary['debug'] = 'yes'


#######################################
#######################################
#                                     #
#                 MAIN                #
#                                     #
#######################################

getparameter(sys.argv[0:])
if argdictionary['vmname'] == '':
    print "VM-Name not set"
    sys.exit (1)

logger = Logger(argdictionary['logdir'], argdictionary['vmname'])

if argdictionary['debug'] == 'yes':
    logger.setLogLevel(logging.DEBUG)
	
if 	os.path.isfile(argdictionary['manager-key']):
	if os.stat(argdictionary['manager-key']).st_size == 0:
		argdictionary['mpassword'] = getpass.getpass('Empty key file. Please provide password for user ' + argdictionary['username'] + ': ')
else:
	argdictionary['mpassword'] = getpass.getpass('No SSH key provided. Please provide password for user ' + argdictionary['username'] + ': ')
	
	
ovmcli = OVMcli()
ovmcli.login(argdictionary)
ovmcli.getDataVM(argdictionary['vmname'])

if argdictionary['online'] == 'no':
    vmstate = ovmcli.getvmState()
    if vmstate != 'Stopped':
        logging.critical("VM " + argdictionary['vmname'] + ' is in state ' + vmstate)
        logging.critical("VM must be in state Stopped. Aborting script!")
        sys.exit(99)

virtualDiskList = []
virtualDiskList = ovmcli.getvmVirtualDisks4VM()
ovmServerHostname = ovmcli.getovmSever4VM()

# write vm-configuration with ConfigParser for later restoring the configuration
configfile = argdictionary['logdir'] + '/' + argdictionary['vmname'] + '.cfg'
ovmcli.writeConfiguration(configfile)


sshlogfile = argdictionary['logdir'] + '/' + argdictionary['vmname'] + '_ssh.log'

if 	os.path.isfile(argdictionary['server-key']):
	if os.stat(argdictionary['server-key']).st_size == 0:
		argdictionary['spassword'] = getpass.getpass('Empty key file. Please provide password for root on ' + ovmServerHostname + ': ')
else:
	argdictionary['spassword'] = getpass.getpass('No SSH key provided. Please provide password for root on ' + ovmServerHostname + ': ')

ovmsssh = OVMSssh(sshlogfile)
ovmsssh.login(ovmServerHostname)
ovmcli.printVMDetails()
virtualDiskMappingList = ()
if argdictionary['compression']:
	TarFileLoc = ovmsssh.createSnapshot(argdictionary['vmname'], virtualDiskList, virtualDiskMappingList, True)
else:
	ovmsssh.createSnapshot(argdictionary['vmname'], virtualDiskList, virtualDiskMappingList, False)
	
if argdictionary['dest-dir']:
	argdictionary['dest-dir'] = os.path.normpath(argdictionary['dest-dir']) + '/'
        print 'Transfering {}:{} to {}'.format(ovmServerHostname, TarFileLoc, argdictionary['dest-dir'])
		print 'Transfering ' + ovmServerHostname + ':' + TarFileLoc + ' to ' + argdictionary['dest-dir']
	ovmsssh.transferSnapshot(argdictionary, ovmServerHostname, TarFileLoc)
	SnapshotDir = TarFileLoc.rstrip('.tar.gz')
	print 'Removing snapshot ' + ovmServerHostname + ':' + TarFileLoc
	ovmsssh.removeSnapshot(TarFileLoc, SnapshotDir)

ovmcli.logout()
ovmsssh.logout


