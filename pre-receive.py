#!/usr/bin/env python
'''
This is a Python script which will be used as a pre-receive hook.
The purpose of this hook is to check whether or not a user is
allowed to make changes to any particular file on a particular
branch of a repository.
'''
import re
import sys
import json
import requests
import commands
from access_map import INDIR

with open("/opt/git/gitlab-shell/gitlab-shell.log","a") as logfile:
    logfile.write("############################")

# Read in each ref that the user is trying to update
DEPLOYMENT_TAG_RE = "(\d+\.){3,}\d+-\d+(_P\d+-+\d+)?_[A-z]+"
PRODUCT_TAG_RE = "(\d+\.){3,}\d+-\d+(_P\d+-+\d+)?(_[A-z]+){2}"
ZYCUS_EMAIL_RE = "(\w)+\.(\w)+@zycus\.com"

PRIVATE_TOKEN = "tv6hrsqa7rt2VxQY26Mm"
USERS_API = "http://gitlab.zycus.com/api/v3/users"

GIT_LOG_PATH = "/opt/git/gitlab-shell/gitlab-shell.log"


# INDIR = {"branch_name":{"file_path":["email_list"]}}
#INDIR = {
#    "master" : {
#        "dira" : ["vicky.deshpande@zycus.com"],
#        "file1" : ["git-admin@zycus.com"]
#        },
#    "Development" : {
#        "dira" : ["vicky.deshpande@zycus.com"],
#        "file1" : ["vicky.deshpande@zycus.com"]
#        }
#    }

BAD_SIGNAL = '0'
LINE_SEPARATOR = "------------------------------------------------------"



if len(sys.argv) != 4:
    sys.exit(1)

OLD_REV = sys.argv[1]
NEW_REV = sys.argv[2]
REFSPEC = sys.argv[3]

def get_keys_dir():
    '''
    INPUT - No input

    OUTPUT - A directory of the form
             {user_email : list_of_keys_owned_by_user}
    '''
    head = requests.get(USERS_API + "?per_page=100&private_token=" + PRIVATE_TOKEN)
    head = head.headers
    total_pages = head['X-Total-Pages']
    total_pages = int(total_pages)
    user_list = []
    key_dir = dict()
    for page_num in range(total_pages):
        ulist = requests.get(USERS_API + "?per_page=100&page=" + str(page_num + 1) + "&private_token=" + PRIVATE_TOKEN)
        ulist = ulist.text
        ulist = json.loads(ulist)
        user_list = user_list + ulist
    for user in user_list:
        uid = user['id']
        klist = requests.get(USERS_API + "/" + str(uid) + "/keys?private_token=" + PRIVATE_TOKEN)
        klist = klist.text
        klist = json.loads(klist)
        if klist:
            key_dir[user['email']] = klist
    return key_dir

def get_current_project_path():
    '''
    INPUT - No input

    OUTPUT - Path to the current git repository on server
    '''
    pwd = commands.getoutput("pwd")
    repo_path = pwd.split('/custom_hooks')[0]
    return repo_path

def get_key_id():
    '''
    INPUT - No input

    OUTPUT - The ID assigned by Gitlab to the SSH public key
             used for current communication
    '''
    current_repo = get_current_project_path()
    logs = commands.getoutput("tail " + GIT_LOG_PATH)
    logs = logs.split("\n")
    logs = logs[::-1]
    key_id = 'None'
    for log in logs:
        if current_repo in log:
            key_id = log.split()[-1]
            key_id = key_id.split('-')[-1]
            key_id = key_id.strip('.')
    return key_id

def check_email():
    '''
    INPUT - No input

    OUTPUT - Email address of the user who pushed the commit
    '''
    key_id = get_key_id()
    keydir = get_keys_dir()
    for user in keydir.keys():
        key_list = keydir[user]
        for key in key_list:
            if str(key['id']) == str(key_id):
                return user
    else:
        return "NONE"


def check_empty_sha(sha):
    '''
    INPUT - An SHA representing a commit

    OUTPUT - 'FAIL' if HASH consists entirely of '0'
             i.e. it is an empty HASH; 'PASS' otherwise
    '''
    sha = set(sha)
    sha = list(sha)
    if len(sha) == 1:
        if sha[0] == BAD_SIGNAL:
            return "FAIL"
    return "PASS"

def get_changed_files(oldrev, newrev):
    '''
    INPUT - SHA of last commit of last push as 'oldrev'
            and last commit of incoming push as 'newrev'

    OUTPUT - A single string containing a newline separated
             list of changed files if any file has been
             changed since the last push received by the
             server, 'NONE' otherwise
    '''
    command = "git diff --name-only " + oldrev + " " + newrev
    cstatus, cname = commands.getstatusoutput(command)
    if cstatus == 0:
        return cname
    return "NONE"



def get_commit_branch(refspec_name):
    '''
    INPUT - Name of the refspec that will be changed as
            observed by the server

    OUTPUT - Exact name of the branch that will be affected
             if any is found, 'NONE' otherwise
    '''
    command = "git rev-parse --symbolic --abbrev-ref " + refspec_name
    bstatus, bname = commands.getstatusoutput(command)
    if bstatus == 0:
        return bname
    return "NONE"

def get_push_details(rev):
    '''
    INPUT - SHA representing a commit

    OUTPUT - details represented by the said incoming SHA
             if any, 'NONE' otherwise
    '''
    command = "git show " + rev
    dstatus, doutput = commands.getstatusoutput(command)
    if dstatus == 0:
        doutput = doutput.split('\n')
        return doutput
    return "NONE"

def get_author_line(push_details):
    '''
    INPUT - The details of the commit as received from get_push_details()

    OUTPUT - A string containing the name and email of the author of the commit
             as mentioned in the incoming details if any, 'NONE' otherwise
    '''
    author_line_list = [line for line in push_details if line.startswith("Author")]
    if len(author_line_list) == 1:
        author_line = author_line_list[0]
        author_line = author_line.split(' ')
        return author_line
    return "NONE"

def get_author_name(aline):
    '''
    INPUT - The string received from get_author_line()

    OUTPUT - The name as specified in the incoming string if any, 'NONE' otherwise
    '''
    if len(aline) == 4:
        author_name = aline[1] + " " + aline[2]
        return author_name
    if len(aline) == 3:
        author_name = aline[1]
        return author_name
    return "NONE"

#def check_email(email):
#    '''
#    INPUT - The section denoting the email as found in the strng
#            received from get_author_line()
#
#    OUTPUT - The exact email extracted from the input
#             provided it matches the criteria to be a zycus internal email;
#             'NONE' otherwise
#    '''
#    if email.startswith('<') and email.endswith('>'):
#        email = email[1:-1]
#    if re.match(ZYCUS_EMAIL_RE, email):
#        return email
#    return "NONE"


def get_author_email(aline):
    '''
    INPUT - The string received from get_author_line()

    OUTPUT - The section of the string denoting the email of the author
             if any is found;
             'NONE' otherwise
    '''
    if len(aline) == 4:
        author_email = aline[3]
        author_email = check_email()
        return author_email
    if len(aline) == 3:
        author_email = aline[2]
        author_email = check_email()
        return author_email
    return "NONE"

def get_diff_line(push_details):
    '''
    INPUT - The details of the commit as received from get_push_details()

    OUTPUT - A string which is a line denoting the last file changed
             in the corresponding commit if any,
             'NONE' otherwise
    '''
    diff_line_list = [line for line in push_details if line.startswith("diff")]
    if len(diff_line_list) == 1:
        diff_line = diff_line_list[0]
        return diff_line
    return "NONE"

def get_change_root(dline):
    '''
    INPUT - The string received from get_diff_line()

    OUTPUT - The exact file that has been changed
             if any corresponding to the current commit,
             'NONE' otherwise
    '''
    dline = dline.split(" ")
    if len(dline) == 4:
        change_root = dline[2]
        return change_root
    return "NONE"


def check_push_root(refspec, old_rev, new_rev, indir):
    '''
    INPUT - Name of the refspec that will be changed
            as observed by the server as 'refspec';
            SHA of the last commit of the last push
            present with the server as 'old_rev';
            SHA of the last commit of the incoming push
            to the server as 'new_rev';
            Dictionary specifying the branch,
            directory, file and users to be monitored as 'indir'

    OUTPUT - 'FAIL' if the author of the commit is not allowed to push
             on a specific file and/or directory on a specific branch
             provided the same has been attempted,
             'PASS' otherwise
    '''
    commit_branch = get_commit_branch(refspec)
    if commit_branch == "NONE":
        print "NO COMMIT BRANCH COULD BE FOUND!!!"
        return "FAIL"
    push_details = get_push_details(new_rev)
    if push_details == "NONE":
        print "NO PUSH DETAILS COULD BE FOUND!!!"
        return "FAIL"
    else:
        author_line = get_author_line(push_details)
        if author_line == "NONE":
            print "NO AUTHOR LINE COULD BE FOUND!!!"
            return "FAIL"
        else:
            author_name = get_author_name(author_line)
            if author_name == "NONE":
                print "NO AUTHOR NAME COULD BE FOUND!!!"
                return "FAIL"
            author_email = check_email()
            if author_email == "NONE":
                print "NO AUTHOR EMAIL COULD BE FOUND!!!"
                return "FAIL"
            diff_line = get_diff_line(push_details)
            if diff_line == "NONE":
                print "NO DIFF LINE COULD BE FOUND!!!"
                return "PASS"
            else:
                changed_files_list = get_changed_files(old_rev, new_rev)
                if changed_files_list == "NONE":
                    print "NO CHANGED FILES WERE FOUND!!!"
                    return "FAIL"
                else:
                    changed_files_list = changed_files_list.split("\n")
                    if indir.keys():
                        for branch_name in indir.keys():
                            if branch_name == commit_branch:
                                branch_files = indir[branch_name]
                                if branch_files.keys():
                                    for file_path in branch_files.keys():
                                        for filename in changed_files_list:
                                            if filename.startswith(file_path):
                                                file_users = branch_files[file_path]
                                                if file_users:
                                                    if not author_email in file_users:
                                                        print LINE_SEPARATOR
                                                        print "The user " + author_email + " is not permitted to make changes to the file " + file_path + " on the branch " + branch_name + " of this project"
                                                        print LINE_SEPARATOR
                                                        return "FAIL"
                    return "PASS"


OLD_REV_CHECK = check_empty_sha(OLD_REV)
NEW_REV_CHECK = check_empty_sha(NEW_REV)


if OLD_REV_CHECK == "FAIL":
    print "THIS CORRESPONDS TO NEW BRANCH CREATION"
    sys.exit(0)

if NEW_REV_CHECK == "FAIL":
    COMMIT_BRANCH = get_commit_branch(REFSPEC)
    if COMMIT_BRANCH == "Development":
        print "DELETING THE BRANCH 'Development' IS NOT ALLOWED!!!"
        sys.exit(1)
    sys.exit(0)


PUSH_ROOT_STATUS = check_push_root(REFSPEC, OLD_REV, NEW_REV, INDIR)

if PUSH_ROOT_STATUS == "FAIL":
    sys.exit(1)
else:
    sys.exit(0)




#if change_src.startswith("a/dira"):
#    if author_email in to_block_email:
#        print author_email + "is not allowed to push changes to the directory dira"
#    sys.exit(1)

#if not 'tag' in op.split("\n")[0]:
#    print "WARNING!!! THE PUSH IS NOT ACCOMPANIED WITH A TAG TAGGED!!!"
#    sys.exit(1)
#else:
#    tagline = op.split("\n")[0]
#    tagname = tagline.split()[1]
#    if re.match(Product_Tag_RE, tagname):
#        print tagname + " is a Product Script Tag"
#    elif re.match(Deployment_Tag_RE,tagname):
#        print tagname + " is a Deployment Repo Tag"
#    else:
#        print "Tag format is invalid"
#        sys.exit(1)


# Abort the push
# sys.exit(1)

