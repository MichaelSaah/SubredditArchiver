import praw, sys, re, json, time, os, logging, argparse, tarfile, shutil
from config import *

# SymVer
VERSION = "v0.1.0"

subredditName = None
startTime = int(time.time())
endTime = None


def usage():
    print(str(sys.argv[0]) + " <subreddit name>")


def cli_arguments():
    """ Process the command line arguments """
    global OUTPUT_BASE
    parser = argparse.ArgumentParser(description='Archive the contents of a reddit subreddit.')
    parser.add_argument('subreddit', metavar='subreddit', type=str,
                        help='the subreddit name')
    parser.add_argument('--log', dest='loglevel', default="ERROR",
                        help='Logging Level')
    parser.add_argument('--output-dir', dest='OUTPUT_BASE', type=str, default=OUTPUT_BASE,
                        help='specify a new destination directory for the output')
    parser.add_argument('--no-wiki', dest='wiki', action='store_const', const=False, default=True,
                        help='don\'t archive the contents of the subreddit\'s wiki')
    parser.add_argument('--no-wiki-revisions', dest='wikiRevisions', action='store_const', const=False, default=True,
                        help='don\'t archive revisions of the subreddit\'s wiki pages')
    parser.add_argument('--no-submissions', dest='submissions', action='store_const', const=False, default=True,
                        help='don\'t archive the subreddit\'s submissions')
    parser.add_argument('--no-compress', dest='compress', action='store_const', const=False, default=True,
                        help='don\t compress the output')
    parser.add_argument('--keep', dest='keep', action='store_const', const=True, default=False,
                        help='keep the raw directory after compressing')
    parser.add_argument('--limit', dest='limit', default=100, type=int,
                        help='the max number of submissions to archive')


    args = parser.parse_args()

    OUTPUT_BASE = args.OUTPUT_BASE

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)
    logging.basicConfig(level=numeric_level)

    return args


def archive_wiki(subreddit, wikiDir, archiveRevisions = True):
    """ 
    Archive the wiki pages for the supplied subreddit 
    
    :param subreddit: A PRAW Subreddit object
    
    :param wikiDir: The path to the directory for the wiki pages
    
    """
    for wikipage in subreddit.wiki:
        logging.info("Processing Wiki Page: " + wikipage.name)
        try:
            pageFile = os.path.join(wikiDir, wikipage.name)
            if not os.path.isdir(os.path.dirname(pageFile)):
                os.makedirs(os.path.dirname(pageFile))
            # for revision in wikipage.revisions():
            #     print(revision['page'])
            with open(pageFile+".md", "w") as pageFileHandler:
                pageFileHandler.write(wikipage.content_md)
                pageFileHandler.close()
            if archiveRevisions:
                for revision in wikipage.revisions():
                    logging.info("Processing Wiki Page: " + wikipage.name + " revision: " + revision['id'])
                    try:
                        with open('.'.join([pageFile, revision['id'], "md"]), "w") as pageRevisionFileHandler:
                            pageRevisionFileHandler.write(revision['page'].content_md)
                            pageRevisionFileHandler.close()
                        time.sleep(SLEEP_SEC)
                    except Exception as revisionException:
                        logging.error("Ran into an Exception processing wiki page " + wikipage.name +
                              " revision " + revision['id'])
                        print(revisionException)
        except Exception as pageException:
            logging.error("Ran into an Exception processing wiki page " + wikipage.name)
            print(pageException)


def archive_submissions(subreddit, submissionDir, limit):
    """
    Archive a subreddit's submissions
    :param subreddit:
    :param submissionDir:
    :return:
    """
    logging.info("Processing Submissions")
    count = 0
    if not os.path.isdir(submissionDir):
        os.makedirs(submissionDir)

    submission_attrs = [
        "id",
        "shortlink",
        "fullname",
        "approved_by",
        "archived",
        "author.name",
        "author_flair_text",
        "banned_by",
        "contest_mode",
        "created",
        "created_utc",
        "distinguished",
        "domain",
        "downs",
        "edited",
        "gilded",
        "hidden",
        "is_self",
        "likes",
        "locked",
        "media",
        "media_embed",
        "name",
        "num_comments",
        "num_reports",
        "over_18",
        "permalink",
        "quarantine",
        "removal_reason",
        "score",
        "secure_media",
        "secure_media_embed",
        "selftext",
        "selftext_html",
        "spoiler",
        "stickied",
        "subreddit_name_prefixed",
        "subreddit_type",
        "subreddit_id",
        "thumbnail",
        "title",
        "ups",
        "upvote_ratio",
        "url",
        "post_hint",
        "preview"
    ]

    for submission in subreddit.top('all',limit=limit):
        logging.info("Processing Submission: " + submission.id)
        print(submission.id)
        count+=1

        submissionObj = dict()
        for a in submission_attrs:
            if '.' in a: # only handles one level of depth, need to alter if you need more
                parent,child = a.split('.')
                if hasattr(submission, parent) and hasattr(getattr(submission, parent), child):
                    name = parent + '_' + child
                    submissionObj[name] = getattr(getattr(submission, parent), child)
            else:
                if hasattr(submission, a):
                    submissionObj[a] = getattr(submission, a)

        comment_attrs = [
            "fullname",
            "is_root",
            "author.name",
            "submission.id",
            "body",
            "can_mod_post",
            "controversiality",
            "created",
            "created_utc",
            "depth",
            "downs",
            "edited",
            "gilded",
            "id",
            "is_submitter",
            "name",
            "no_follow",
            "num_reports",
            "parent_id",
            "score",
            "ups",
            "score_hidden",
            "stickied"
        ]

        submission.comments.replace_more(limit=None)
        submissionObj["comments"] = []
        for comment in submission.comments.list():
            commentObj = dict()
            for a in comment_attrs:
                if '.' in a: # only handles one level of depth, need to alter if you need more
                    parent,child = a.split('.')
                    if hasattr(comment, parent) and hasattr(getattr(comment, parent), child):
                        name = parent + '_' + child
                        commentObj[name] = getattr(getattr(comment, parent), child)
                else:
                    if hasattr(comment, a):
                        commentObj[a] = getattr(comment, a)
            submissionObj["comments"].append(commentObj)

        with open(os.path.join(submissionDir, '.'.join([submission.id, "json"])), "w") as submissionFileHandler:
            submissionFileHandler.write(json.dumps(submissionObj))
    logging.info("Finished processing {0} submissions".format(count))
    pass


def archive_subreddit_information(subreddit, baseDir):
    """
    Archive basic information about the subreddit
    :param subreddit:
    :param baseDir:
    :return:
    """
    with open(os.path.join(baseDir, "rules.json"), "w") as rulesFileHandler:
        rulesFileHandler.write(json.dumps(subreddit.rules()))
    subredditObj = {
        "name": subreddit.display_name,
        "description": subreddit.description,
        "title": subreddit.title
    }
    with open(os.path.join(baseDir, subreddit.display_name + ".json"), "w") as fileHandler:
        fileHandler.write(json.dumps(subredditObj))
    pass


def write_meta(baseDir):
    """
    Write the archiveData.json meta data file to the archive for future reference
    :param baseDir:
    :return:
    """
    global startTime, subredditName, endTime, META_EXTRA
    metaData = {
        "archived_at": startTime,
        "started_at": startTime,
        "archived_with": "SubredditArchiver " + VERSION,
        "subreddit": subredditName,
        "command_line_arguments": args._get_kwargs()
    }
    if endTime:
        metaData['finished_at'] = endTime
    if META_EXTRA:
        metaData['extra_data'] = META_EXTRA
    with open(os.path.join(baseDir, "archiveData.json"), "w") as metaDataFileHandler:
        metaDataFileHandler.write(json.dumps(metaData))


def compress_archive(baseDir, startTime):
    """
    Create a compressed tarball of the archive.
    :param baseDir: 
    :param startTime: 
    :return: 
    """
    global subredditName
    workingDir = os.getcwd()
    try:
        os.chdir(os.path.dirname(baseDir)) # chdir to the output directory to combat tar extensive paths
        tarfileName = os.path.join('.'.join([subredditName, str(startTime), "tar.gz"]))
        with tarfile.open(tarfileName, "w:gz") as archiveFile:
            archiveFile.add(os.path.basename(baseDir))
            archiveFile.close()
    except Exception as e:
        logging.error("Something went wrong compressing the archive.")
    os.chdir(workingDir)

args = cli_arguments()
print("Archiving r/" + args.subreddit)

reddit = praw.Reddit(client_id=CLIENT_ID,
                     client_secret=CLIENT_SECRET,
                     user_agent = "subreddit-archiver:v0.1 (by /u/chpwssn github.com/chpwssn)")
reddit.read_only
subreddit = reddit.subreddit(args.subreddit)


# Build Paths
baseDir = os.path.abspath(os.path.join(OUTPUT_BASE, args.subreddit, str(startTime)))
wikiDir = os.path.join(baseDir, "wiki")
submissionDir = os.path.join(baseDir, "submissions")

if not os.path.exists(baseDir):
    os.makedirs(baseDir)

# Write Archive meta data
write_meta(baseDir)

archive_subreddit_information(subreddit, baseDir)

# Get Submissions
if args.submissions:
    archive_submissions(subreddit, submissionDir, args.limit)

# Get Wiki Pages
if args.wiki:
    archive_wiki(subreddit, wikiDir, args.wikiRevisions)

# Log End Time and Rewrite Meta File
endTime = time.time()
write_meta(baseDir)

if args.compress:
    compress_archive(baseDir, startTime)
    if not args.keep:
        shutil.rmtree(baseDir)
