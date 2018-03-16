import re
import sys
import json
import requests
import commands

OLDREF = sys.argv[1]
NEWREF = sys.argv[2]
print sys.argv
print OLDREF
print NEWREF

JENKINS_SERVER = "enter jenkins server ip here"
JENKINS_PORT = "enter jenkins port here"
JENKINS_USER = "enter jenkins user here"
JENKINS_USER_API_TOKEN = "enter jenkins api token of the user"
jobname = "enter the name of the jenkins job here"
BAD_SIGNAL = '0'

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

NEWREF = NEWREF.strip()


def get_commit_details(sha):
    details = commands.getoutput("git show " + sha)
    details_list = details.split("\n")
    return details_list

def get_merge_branches(dlist):
    mdict = dict()
    for line in dlist:
        if line.strip():
            if line.strip().startswith("Merge branch"):
                mline = line
                mline = mline.split()
                mdict["src"] = mline[2].strip("'")
                mdict["dest"] = mline[4].strip("'")
                return mdict
    else:
        return "FAIL"

def get_build_number(dlist):
    mdict = get_merge_branches(dlist)
    src = mdict["src"]
    if src.startswith("ERT"):
        src = src.split("_")
        print src
        bnum = src[2]
        return bnum
    return "NO_BNUM"

def get_jenkins_crumb():
    print "in getting crumb"
    url = "http://" + JENKINS_USER + ":" + JENKINS_USER_API_TOKEN + "@" + JENKINS_SERVER + ":" + JENKINS_PORT + "/crumbIssuer/api/json"
    print url
    crumb = requests.get(url)
    crumb = crumb.text
    crumb = json.loads(crumb)
    print crumb.keys()
    crumb = crumb["crumb"]
    return crumb

def trigger_the_URL(dlist):
    bnum = get_build_number(dlist)
    crumb = get_jenkins_crumb()
    #URL = "http://" + JENKINS_SERVER + ":" + JENKINS_PORT + "/job/" + jobname + "/" + bnum + "/input/Approval/proceedEmpty"
    print URL
    headers = {'Jenkins-Crumb' : crumb}
    print "start trigger"
    trigger = requests.post(URL, auth=(JENKINS_USER, JENKINS_USER_API_TOKEN), headers=headers)
    print "end trigger"


print "checking old ref"
old_ref_state = check_empty_sha(OLDREF)
print old_ref_state
print "checking new ref"
new_ref_state = check_empty_sha(NEWREF)
print new_ref_state

if old_ref_state == "FAIL":
    print "This corresponds to a new branch creation"
    exit(0)
if new_ref_state == "FAIL":
    print "This corresponds to an existing branch deletion"
    exit(0)


print "getting details"
details_list = get_commit_details(NEWREF)
print details_list
print "got getails"
print "getting merge branches"
merge_dict = get_merge_branches(details_list)
print merge_dict
print "got merge branches"
if not merge_dict == "FAIL":
    print "getting bnum"
    bnum = get_build_number(details_list)
    print bnum
    print "got bnum"
    if not bnum == "NO_BNUM":
        print "getting crumb"
        crumb = get_jenkins_crumb()
        print "got crumb"
        print "triggering"
        trigger_the_URL(details_list)
        print "triggered"
