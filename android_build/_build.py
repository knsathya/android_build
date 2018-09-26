import os
import pyshell
import logging
from future.builtins import str
import multiprocessing
import tempfile
from jsonparser import JSONParser
import pkg_resources


set_val = lambda k, v: v if k is None else k
valid_str = lambda x: True if x is not None and isinstance(x, str) and len(x) > 0 else False

def which(cmd):
    for path in os.environ["PATH"].split(os.pathsep):
        cmd_path = os.path.join(path, cmd)
        if os.access(cmd_path, os.X_OK):
            return cmd_path

    return None

class BuildAndroid(object):

    def _get_repo_script(self, repo):
        # If not valid repo is given, check if repo exists in PATH
        if not valid_str(repo):
            if which("repo") is None:
                self.logger.error("No valid repo command found")
                return False
            else:
                self.repo = which("repo")
                return True
        else:
            self.repo = os.path.abspath(os.path.join(self.src, 'repo-bin', 'repo'))
            if not os.path.exists(os.path.join(self.src, 'repo-bin')):
                os.makedirs(os.path.join(self.src, 'repo-bin'))
            if repo.startswith('http'):
                self.sh.cmd("curl %s > %s" % (repo, self.repo), shell=True)
            elif os.path.exists(os.path.abspath(repo)):
                self.logger.info(self.sh.cmd("cp %s %s" % (repo, self.repo), shell=True))
            else:
                self.logger.error("Invalid repo %s", repo)
                return False

            return True

        return False

    def repo_init(self, url=None, manifest=None, branch=None, options=''):

        cmd = [self.repo, 'init']

        if valid_str(url):
            cmd.append('-u')
            cmd.append(url)

        if valid_str(manifest):
            cmd.append('-m')
            cmd.append(manifest)

        if valid_str(branch):
            cmd.append('-b')
            cmd.append(branch)

        if valid_str(options):
            cmd.append(options)

        ret = self.sh.cmd(' '.join(cmd), shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

        return ret[0]

    def repo_sync(self, threads=((multiprocessing.cpu_count()/4) * 3), options=''):
        if not self.valid:
            self.logger.error("Invalid repo")
            return False

        ret = self.sh.cmd('%s sync -c -j%d %s' % (self.repo, threads, options), shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

    def repo_abandon_branch(self, branch='master'):
        if not self.valid:
            self.logger.error("Invalid repo")
            return False

        ret = self.sh.cmd('%s abandon %s' % (self.repo, branch), shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

    def repo_create_branch(self, branch='master'):
        if not self.valid:
            self.logger.error("Invalid repo")
            return False

        ret = self.sh.cmd('%s start %s --all' % (self.repo, branch), shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

    def repo_reset(self):
        if not self.valid:
            self.logger.error("Invalid repo")
            return False

        ret = self.sh.cmd('%s forall -vc "git reset --hard"' % self.repo, shell=True)
        if ret[0] != 0:
            self.logger.error(ret)
        ret = self.sh.cmd(self.repo, 'sync -d', shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

        return True

    def get_targets(self):

        if not self.valid:
            self.logger.error("Invalid repo")
            return None

        ret = self.sh.cmd('source build/envsetup.sh;echo ${LUNCH_MENU_CHOICES[*]}', shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

        return ret[1].split(' ') if ret[0] == 0 else []

    def clean_all(self):
        if not self.valid:
            self.logger.error("Invalid repo")
            return False

        ret = self.sh.cmd('rm -fr %s/*' % (self.out), shell=True)
        if ret[0] != 0:
            self.logger.error(ret)

        return True

    def clean_kernel(self):
        if self.target is None:
            self.logger.error("No valid target found")
            return False

        target_dir = os.path.join(self.out, 'target', 'product', self.target)
        if not os.path.exists(target_dir):
            self.logger.error("Target dir not found")
            return False

        if os.path.exists(os.path.join(target_dir, 'obj', 'kernel')):
            self.sh.cmd("rm -fr %s" % os.path.join(target_dir, 'obj', 'kernel'), shell=True)

        return True

    def cherrypick_patches(self, path, urls=[]):
        # todo: need to implement the logic
        return True

    def update_project_list(self, project_list=[]):
        for project in project_list:
            status = self.update_project(project["project-dir"], project["new-dir"], project["rurl"])
            if not status:
                return False

        return True

    def update_project(self, project_dir, new_dir=None, remote=None):

        self.logger.info(locals())

        if not valid_str(project_dir):
            self.logger.error("Invalid project dir %s", project_dir)
            return False

        if not project_dir.startswith('/'):
            project_dir = os.path.join(self.src, project_dir)

        if not os.path.exists(os.path.abspath(project_dir)):
            self.logger.error("Invalid project dir %s", project_dir)
            return False

        if valid_str(new_dir) and not os.path.exists(os.path.abspath(new_dir)):
            self.logger.error("Invalid new dir %s", new_dir)
            return False

        if valid_str(new_dir):
            if os.path.exists(os.path.abspath(project_dir) + '.old'):
                ret = self.sh.cmd("rm %s" % os.path.abspath(project_dir) + '.old', shell=True)
                if ret[0] != 0:
                    self.logger.error(ret)

            ret = self.sh.cmd("mv %s %s" % (os.path.abspath(project_dir), os.path.abspath(project_dir) + '.old'),
                              shell=True)
            if ret[0] != 0:
                self.logger.error(ret)

            ret = self.sh.cmd("ln -s %s %s" % (os.path.abspath(new_dir), os.path.basename(project_dir)), shell=True,
                              wd=os.path.dirname(os.path.abspath(project_dir)))
            if ret[0] != 0:
                self.logger.error(ret)

        if valid_str(remote):
            remote = remote.split(',')
            self.logger.info(remote)
            git = pyshell.GitShell(wd=os.path.abspath(project_dir), init=True,
                                   remote_list=[(remote[0],remote[1])], fetch_all=True,
                                   logger=self.logger, stream_stdout=True)
            git.cmd('reset --hard')
            git.checkout(remote[0], remote[2])

        self.logger.info("Updating project %s successful", project_dir)

        return True

    def make_target(self, product, target, options='', threads=((multiprocessing.cpu_count()/4) * 3)):

        if not self.valid:
            self.logger.error("Invalid repo")
            return False

        cmds = 'source build/envsetup.sh;lunch %s;make %s -j%d %s;' % (product, target, threads, options)

        ret = self.sh.cmd(cmds, shell=True)
        if ret[0] != 0:
            self.logger.error("Make target %s %s failed" % (product, target))
            self.logger.error(ret[1])
            return False

        return True

    def upload_image(self, mode, lurl, rurl, rname="", msg=""):
        # todo: need to implement the logic

        if mode == 'cp':
            cmd = "cp %s %s" % (lurl, rurl)
            ret = self.sh.cmd(cmd, shell=True)
            if ret[0] != 0:
                self.logger.error("%s failed", cmd)
                self.logger.error(ret[1])
                return False
        elif mode == 'scp':
            cmd = "cp %s %s" % (lurl, rurl)
            ret = self.sh.cmd(cmd, shell=True)
            if ret[0] != 0:
                self.logger.error("%s failed", cmd)
                self.logger.error(ret[1])
                return False

        return True

    def auto_build(self):
        if self.cfg is None or self.obj is None:
            self.logger.error("Invalid config file")
            return False

        #repo init
        self.repo_init(self.cfg["repo-init-params"]["url"],
                       self.cfg["repo-init-params"]["manifest"],
                       self.cfg["repo-init-params"]["branch"])

        self.repo_abandon_branch()

        #repo sync
        self.repo_sync(options=self.cfg["repo-sync-params"]["options"])
        self.repo_create_branch()

        #Make build
        for item in self.cfg["target-list"]:

            print item

            # Check if you want to continue the build
            if not item["enable-build"]:
                continue

            # Check if obj needs to be cleaned
            if item["obj-clean"] == 'all':
                self.clean_all()
            elif item["obj-clean"] == 'kernel':
                self.clean_kernel()

            #Update if any projects needs to be updated
            status = self.update_project_list(item["project-update-list"])
            if not status:
                self.logger.error("project update list failed")
                continue

            # Cherry pick if any patches are required.
            status  = self.cherrypick_patches(self.src, item["cherry-pick-list"])
            if not status:
                self.logger.error("Cherry pick list failed")
                continue

            # Make the build
            status = self.make_target(item["product"], item["target"], item["options"])
            if not status:
                self.logger.error("Build make command failed")
                continue

            # Check if image needs to be uploaded
            if item["upload-image"]:
                self.upload_image(item["mode"], item["lurl"], item["rurl"], item["rname"], item["msg"])

        return True

    def __init__(self, src_dir=None, out_dir=None, repo_url=None, cfg = None, logger=None):
        self.logger = logger or logging.getLogger(__name__)

        self.src = os.path.abspath(set_val(src_dir, os.getcwd()))
        self.out = os.path.abspath(set_val(out_dir, os.path.join(self.src, 'out')))
        self.repo = '~/bin/repo'
        self.target = None
        self.valid = False
        self.schema = pkg_resources.resource_filename('android_build', 'schemas/android-schema.json')
        self.cfg = None
        self.obj = None

        self.sh =  pyshell.PyShell(wd=self.src, stream_stdout=True)
        self.sh.update_shell()

        if cfg is not None:
            self.obj = JSONParser(self.schema, cfg, extend_defaults=True, os_env=True, logger=logger)
            self.cfg = self.obj.get_cfg()
            repo_url = self.cfg["repo-script"] if valid_str(self.cfg["repo-script"]) else repo_url

        if not self._get_repo_script(repo_url):
            self.logger.error("repo setup failed")
            return None

        self.valid = True


