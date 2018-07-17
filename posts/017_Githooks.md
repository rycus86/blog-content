# Githooks: auto-install client-side hooks checked into Git repositories

Git hooks are a great way to execute custom actions triggered by various Git events on the local machine. In my opinion, they have some shortcomings around installation and reusability that I'm trying to address with the [Githooks](https://github.com/rycus86/githooks) project.

Let's start with discussing these issues around setup, then a potential solution for them, and finally some examples where I found them useful.

## Setup pains

[Git hooks](https://git-scm.com/docs/githooks) normally live inside the `.git/hooks` folders of local repositories. These can contain one executable per trigger event, like `pre-commit` or `post-checkout` that is run by various `git` commands automatically. Sounds magical, what's the problem with this?

The `.git` folder is excluded from version control, it only lives on your machine. To get a hook in place, you either have to copy an executable file with the trigger's name into the `.git/hooks` folder or symlink one into it. The latter is good practise if you want to put the hook files inside the repository, so at least they have version history and people working on the same project can install them easily. But do they? In my experience, anything that you *should optionally* do is often ignored for these sorts of things.

The next problem is the fact that you can have one of these files per event. If you want to execute multiple actions for a single trigger, you could write a longer Bash script, code it up in a language that you can compile into a single static binary, or split them into multiple files and make the main entrypoint execute the additional functionality living in the split files. This last one probably doesn't make symlinking and working with paths much easier, but it's completely doable as we'll see later.

The last point is about reusability, both for the setup process and the hooks themselves. Done manually, you need to get the hook script and copy or symlink it into each repository you want it applied on, so it's easy to miss this step for some of them. You'd also want your setup to move with you if you switch workstations, without perhaps the setup ceremony described above for each project. You might also want to have these hooks executed for all projects of the same type, for example updating Python or Node dependencies on updates, or running `go fmt` before each commit, etc. With the out-of-the-box setup, you'd have to copy and set up the hooks for each of the projects independently.

Don't get me wrong, I love the concept of Git hooks, and the way they work is pretty nice too. I do think we can make this a bit easier though.

## Previous work

My [Githooks](https://github.com/rycus86/githooks) project is not the first one trying to make more sense of these workflows. There's a pretty popular one at [icefox/git-hooks](https://github.com/icefox/git-hooks) judging by the number of stars. It is written in Bash, supports single repository or global setup, in-repo or external locations for the actual hooks, and comes with a handy helper script. It also doesn't look massively maintained recently, though maybe it just has all the features it should have already.

The [git-hooks](https://github.com/git-hooks/git-hooks) project builds on the previous one with additional features, and it is written Go. This allows for more code and functionality with more robust tests, while still compiling into a single binary. It adds the concept of [community hooks](http://git-hooks.github.io/git-hooks/#community-hooks) with a bit of extra configuration, where you can specify external repositories that hold shared hooks to execute beside the in-repository ones. It also provides self-update capabilities, and better performance in theory, if that is a concern. It also hasn't received any updates in a while, but again this might not reflect whether it's still maintained or not.

Both of these projects look pretty promising, and I encourage you to check out their GitHub repositories, they might just be what you're looking for. If they are not, or you'd like to know about my alternative, keep reading!

## Githooks

The two projects above solve most of the problems I wanted to tackle, but I decided to create my own implementation for specific use-cases I wanted to support. *YMMV*, but you might also find it useful.

I chose Shell to implement more or less the same functionality, and it *should* work with various versions,like `sh`, `ash`, `bash`, etc. It only assumes that `git` is available as an executable on the `PATH`, plus the installation requires either `curl`, `wget`, or manually downloading the installation script. This should make it work on systems without Bash available, like Alpine Linux, and also non-x86 architectures, like a Raspberry Pi or a 64-bit ARM server.

As I just mentioned, the [installation](https://github.com/rycus86/githooks#installation) is done by executing a Shell script. It will try to find the Git template directory, or offer to set one up for you. The same [Shell script](https://github.com/rycus86/githooks/blob/master/base-template.sh) is installed for every [supported hook trigger](TODO) in the hook templates folder. These are copied over to new repositories automatically with `git init` or `git clone`. This means that once you run the installation, any future projects should just work if they contain Githooks-compatible hooks.

This compatibility simply means that you can have a `.githooks` folder at the root of your project, where you can [organize](https://github.com/rycus86/githooks#layout-and-options) your individual hooks into folders. You can have multiple scripts for each trigger event, and all of them will be executed for you, unless they are [ignored](TODO). Maybe you want to add *README* files in the same folders that we wouldn't want to interpret as Shell scripts. You can also have a single file instead of a directory, then the additional benefit is only that you can check it into version control with the rest of your project. You can see the available [layout options](https://github.com/rycus86/githooks#layout-and-options) in the GitHub repo. The individual hook files can be executable, in which case they'll be directly executed, otherwise they are passed as an argument to the `sh` Shell, along with the original command line arguments coming from Git for that particular hook.

> TODO shared hook repos

## Examples

> TODO examples

