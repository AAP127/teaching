#!/usr/bin/env python3
'''
Given a Stepik lesson submission report, create a codePost assignment with submissions and scores via codePost API
Niema Moshiri 2019
'''
from datetime import datetime,timezone
from xlrd import open_workbook
import codepost
EXT = {'java':'java', 'python':'py'}

# main function
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-r', '--roster', required=True, type=str, help="Roster (TSV) (Last, First, Email, PID, Stepik, iClicker, Grade ID)")
    parser.add_argument('-s', '--submissions', required=True, type=str, help="Stepik Lesson Submission Report (XLSX)")
    parser.add_argument('-d', '--deadline', required=True, type=str, help="Deadline (MM/DD/YYYY HH:MM ±HHMM)")
    parser.add_argument('-c', '--course_id', required=True, type=int, help="codePost Course ID")
    parser.add_argument('-a', '--assignment_name', required=True, type=str, help="codePost Assignment Name")
    parser.add_argument('-p', '--point_total', required=True, type=int, help="Total Possible Number of Points")
    parser.add_argument('-l', '--language', required=False, type=str, default=None, help="Language (%s)" % ', '.join(sorted(EXT.keys())))
    args = parser.parse_args()
    if args.language is None:
        file_ext = 'txt'
    else:
        assert args.language.lower() in EXT, "Invalid language: %s (valid: %s)" % (args.language, ', '.join(sorted(EXT.keys())))
        file_ext = EXT[args.language.lower()]
    deadline = datetime.strptime(args.deadline, "%m/%d/%Y %H:%M %z")

    # parse roster
    email_to_stepik = dict()
    for l in open(args.roster):
        if l.startswith("Last Name\t"):
            continue
        last,first,email,pid,stepik,iclicker = [v.strip() for v in l.strip().split('\t')]
        assert email not in email_to_stepik, "Duplicate Email: %s" % email
        email_to_stepik[email] = int(stepik)
    stepik_to_email = {email_to_stepik[email]:email for email in email_to_stepik}
    passed = {email:dict() for email in email_to_stepik}

    # parse submission report
    subs_by_email = {email:dict() for email in email_to_stepik}
    subs = open_workbook(args.submissions).sheet_by_index(0)
    for rowx in range(subs.nrows):
        sub_id,step_id,user_id,last,first,attempt_time,sub_time,status,dataset,clue,reply,reply_clear,hint = subs.row_values(rowx)
        if sub_id == "submission_id":
            continue # header line
        step_id = int(float(step_id)); user_id = int(float(user_id)); reply = eval(reply)
        sub_time = datetime.fromtimestamp(float(sub_time), timezone.utc)
        if user_id not in stepik_to_email or status == 'wrong' or sub_time > deadline:
            continue
        if 'code' not in reply and 'answer' not in reply:
            continue
        email = stepik_to_email[user_id]
        passed[email][step_id] = reply

    # load codePost configuration and course
    codepost_config = codepost.util.config.read_config_file()
    #codepost_course = codepost.course.retrieve(id=args.course_id)

    # create codePost assignment and upload submissions
    codepost_assignment = codepost.assignment.create(name=args.assignment_name, points=args.point_total, course=args.course_id)
    for email in passed:
        codepost_sub = codepost.submission.create(assignment=codepost_assignment.id, students=[email])
        for step_id in sorted(passed[email].keys()):
            code_file = codepost.file.create(name="%d.%s"%(step_id,file_ext), code=passed[email][step_id]['code'], extension=file_ext, submission=codepost_sub.id)
        grade_file = codepost.file.create(name="grade.txt", code="Grade: %d/%d"%(len(passed[email]),args.point_total), extension='txt', submission=codepost_sub.id)
        point_delta = args.point_total - len(passed[email]) # codePost currently assumes subtractive points; update this when they integrate additive
        grade_comment = codepost.comment.create(text='points', startChar=0, endChar=0, startLine=0, endLine=0, file=grade_file.id, pointDelta=point_delta, rubricComment=None)

'''
    print(codepost_course)
    exit()

    # output student grades
    f = open('%s/points.tsv' % args.outdir, 'w')
    for email in passed:
        f.write('%s\t%s\n' % (email,len(passed[email])))
    f.close()

    # output student code
    for email in passed:
        if len([step_id for step_id in passed[email] if 'code' in passed[email][step_id]]) == 0:
            continue
        mkdir("%s/%s" % (args.outdir, email))
        for step_id in sorted(passed[email].keys()):
            if 'code' in passed[email][step_id]:
                f = open("%s/%s/%d.%s" % (args.outdir, email, step_id, file_ext), 'w')
                f.write(passed[email][step_id]['code'])
                f.close()
'''
