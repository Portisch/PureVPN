#!/usr/bin/python

import os
import os.path

purevpnPath=
origResolv = '/etc/resolv.conf'
pureResolv = purevpnPath + "/puredns.conf"
copyOrigResolv = purevpnPath + "/dns.conf"

script_type = os.environ['script_type']

if script_type == 'up':
    if 'foreign_option_2' in os.environ:
        option2 = os.environ['foreign_option_2']
        option2 = option2.split("DNS ",1)[1]

    option1= os.environ['foreign_option_1']
    option1= option1.split("DNS ",1)[1]

    with open(pureResolv,'w') as file1:
        file1.write('nameserver ' + option1 + '\n')
        if option2 is not None:
            file1.write('nameserver ' + option2 + '\n')
        file1.close()

    with open(copyOrigResolv,'w') as file2:
        command = 'cp ' + origResolv + " " + copyOrigResolv
        os.system(command)
        file2.close()

    if os.path.islink(origResolv):
        origResolv = os.readlink(origResolv)

    command1 = 'rm -rf ' + origResolv
    os.system(command1)

    command2 = 'cp ' +  pureResolv + " " + origResolv
    os.system(command2)

if script_type == 'down':
    if os.path.islink(origResolv):
        origResolv = os.readlink(origResolv)

    command1 = 'rm -rf ' + origResolv
    os.system(command1)

    command2 = 'cp ' +  copyOrigResolv + " " + origResolv
    os.system(command2)
