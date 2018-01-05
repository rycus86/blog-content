# Home Lab - Setting up for Docker

In the second post of the series I dive into the details of what is involved setting up for an ever-growing number of applications on a handful of physical servers on my Home Lab.

## Pine64

As I mentioned in [the previous post](TODO), I use small Linux boards from [Pine64](https://www.pine64.org) to host my services. They are ideal for this use-case, don't take up too much space, consume little power but are still powerful enough. Both the [Pine64](https://www.pine64.org/?page_id=1194) and the [Rock64](https://www.pine64.org/?page_id=7147) board features a 64-bits ARMv8 processor with the available memory ranging from 512 MB to 4 GB. My current setup is a bit mixed, having instances with 1, 2 and 4 GB of memory.

> The beauty of this cluster is that you can keep adding new devices whenever you need it. Docker really doesn't care about running on the same or even similar servers.

My only negative about them is their fairly long shipping time. They come from China and it can take close to a month to arrive here in the UK. If this bothers you, have a look at the [Raspberry Pi 3](TODO) which features a similar ARMv8 CPU and is more likely to be available from local distributors. It is also an awesome platform in the sub $50 range, capable of running the 32-bits only official [Raspbian](TODO) distro based on Debian, or you can find a 64-bits capable image from the community. The makers of [HypriotOS](TODO) are doing some pretty cool things with the device and their OS is optimized for Docker usage.

> If you do decide to go with Raspberry Pis, make sure to check out [Alex Ellis' blog](TODO)! He has loads of educational content and tutorials on it and on Docker.

Their available memory maxes out at 1 GB though and I needed something that can comfortably run more memory-hungry applications, like [Elasticsearch](TODO) on the JVM.

## Armbian

The Pine64 community has a wide range of Linux flavors available for the boards. I needed something that plays nicely with Docker, which is Debian and Ubuntu for this CPU architecture. The [Armbian](TODO) guys host great Ubuntu images for lots of ARM boards. The older [Pine64](TODO) has a stable one with a fairly recent kernel version. The [Rock64](TODO) only has a testing build with a slightly older kernel but it seems to work just as well for me so far.

You'll need a micro SD card for these devices. I use [32 GB class 10 SanDisk](TODO) ones but honestly, you could probably get away with 16 or even 8 GB storage to get started. Download the Armbian image from their site, then write it to the SD card.

```shell
$ ls -lh
Armbian_<TODO>.tgz
$ tar xzf Armbian_<TODO>.tgz
$ sudo cp Armbian_<TODO>.img > /dev/mmcblk0
```

It is really as easy as this, unpack the image file and copy it over the SD card device. *YMMV*, make sure you write it to the right device and not your laptop's hard-drive by accident. The SD card also needs to be unmounted during the write. I usually do a `sudo sync` as well after it to flush the write buffer, not a 100% sure though it's necessary.

> If Shell is not your thing, check out [Etcher](TODO) by the awesome [resin.io](TODO) folks for writing SD cards.

It may take a few minutes to finish. Once it's done, insert the card in the board, connect it to the network and give it power. The boot can take around 30-60 seconds. The Armbian installations come with SSH access by default and a predefined root account, you can get the password for it on the download pages. I usually check my router's attached devices list to find the IP address of the newly started device then just log in an do the initial setup over SSH.

You'll need to change the root password on the first login and should create a new user as well to use for further sessions. Log out and log back in with the user you just created. After this is done, make sure the timezone settings are correct on the box, some applications are a bit fussy about it when running in a cluster. [Portainer](TODO) for example uses [JWT authentication](TODO) which needs the time to be in sync.

## Installing Docker

Now that this is done, we can go ahead and install Docker. As I mentioned, the Armbian images are based on Ubuntu which is supported by Docker on the 64-bits ARMv8 platform. This means the installation is done with a one-liner:

```shell
$ curl -fsSL get.docker.com | sudo sh
```

That's it! You may get some warnings and a lot of output about the installation progress, but once finished, your Docker engine is running on the box. If you've followed the setup so far, then you're using the user account, which does not have permissions to interact with the daemon yet.

```shell
$ docker version
<TODO server>
<TODO client no permission>
```

To resolve it, just add your user to the `docker` group:

```shell
$ sudo usermod -aG <your_user> docker -- TODO verify
$ docker version
<TODO server OK>
<TODO client OK>
```

Now you can invoke `docker` commands using your user. *How simple was that?* If you want to test that it works OK, you can check it quickly:

```shell
$ docker run --rm -it alpine echo 'Hello world!'
```

If all is well, then you should see it pulling the `alpine` image from the [Docker Hub](TODO) and printing the `Hello world!` text. I should mention that we didn't have to specify CPU architecture. Recent official images are now *(mostly)* [multi-arch images](TODO), so the exact same command would work on other platforms and CPU architectures as well.

## Compose

If you have a single box at this point and just want to run a couple of services on it, then `docker-compose` might be the easiest option to get started with.

> By experience, the move from Docker Compose to Swarm wasn't as straightforward as I hoped it would be, so if you're planning to expand your home lab, perhaps skip this section and read the Swarm setup section.

You'll need to install the executable first:

```shell
$ sudo apt-get update
$ sudo apt-get install docker-compose -- TODO is it in APT?
```

Once finished, quickly try if it works.

```shell
$ docker-compose version -- TODO is it version?
<TODO version output>
```

*Great!* To configure the services in your __local__ cluster, define them in a [Composefile](TODO) like this:

```yaml
version: '2'
services:

  web:
    image: nginx
    restart: always
    ports:
      - 80:80
    volumes:
      - ./www:/var/htdocs/www # TODO check
  
  internal:
    image: httpd
    restart: always
    ports:
      - 8080:80
    volumes:
      - ./internal-www:/var/htdocs/www # TODO check
```

This example would create two services. The `web` service is an [Nginx](TODO) instance listening on port `80` for HTTP requests. The `internal` service is an [Apache httpd](TODO) instance listening on port `8080` from outside the container - internally it also listens on port 80, but this won't cause any issues when running with Docker. You can have as many applications listening on the same port as you want, they just have to *bind* to different external ports.

It's time to try them! Let's save the above *YAML* content as `docker-compose.yml`, create an index *HTML* file for each of them and check if they serve them up OK.

```shell
$ docker-compose up -d
<TODO output>
$ docker-compose ps
<TODO output>
$ ls
internal-www www -- TODO
$ echo 'Hello!' > www/index.html
$ echo 'Secret hello!' > internal-www/index.html
$ curl -s http://localhost/
Hello!
$ curl -s http://localhost:8080/
Secret hello!
```

The first `docker-compose up -d` command will start both services, pulling the images first if you don't already have them. We can check that they started OK with the `docker-compose ps` command. As you can see above, they are listening on the ports we defined and they have created their respective *docroot* folders. We then created two simple plain-text files with `echo`, both of them called `index.html` and tested they reply it back with `curl`. If you want, you can also see it in your browser, just replace `localhost` with the IP address of your server.

The `restart: always` lines in the Composefile make sure that Docker restarts the containers, should they exit for whatever reason. You can see what they have logged so far as well:

```shell
$ docker-compose logs
<TODO output>
```

> Tip: add `-f` to this command to follow the logs. Just press `Ctrl+C` to exit when you're done.

If you've had enough fun with these, you can easily stop and delete them with a simple command.

```shell
$ docker-compose down
<TODO output>
```

Use `docker-compose stop` instead if you only want to stop the containers but not remove them.

This was fun, *I hope*, but we can do much better than manually editing files over an SSH session and executing commands on the server. You could commit your Composefile into a Git repository and set up basic automation to update the services automatically whenever something changes in it. If your stack is not private and doesn't contain any sensitive data, you could use [GitHub](TODO). Alternatively, sign up for [BitBucket](TODO), where you can have public and private repositories as well. Once your `docker-compose.yml` file is in the cloud, install `git` on the servers and clone the repo in folder. You can now easily commit changes to the file and update the containers on the box:

```shell
$ cd /to/your/cloned/folder
$ git pull
$ docker-compose pull
$ docker-compose up -d
```

The `git pull` will get the changes from your Git repository, then `docker-compose pull` will make sure that you have all the Docker images locally that are defined in the (possibly) updated YAML file. The final `docker-compose up -d` command will start any new services, recreate the ones where the configuration has changed and just leave alone the rest. Now you can use your favourite desktop text editor if you want instead of relying on tools like `vim` or `nano` if you don't like those. On that note though, they are *pretty awesome*, you should definitely look into them!

Having this set up, there's nothing stopping us now to implement a very basic [continuous deployment](TODO) pipeline to automate the updates after any changes in the configuration. We can use [cron](TODO) to do what we've just done automatically every now and then. I used to use this initially and worked OK for me while I only had a handful of services. Let's say we want to check for changes every 15 minutes. Just edit your `cron` schedule with `crontab -e` and add a line like this:

```
0/15 * * * *   cd /to/your/cloned/folder && git pull && docker-compose pull && docker-compose up -d
```

> For bonus points, you could wrap this in a *Bash* script and just invoke that from `cron`.

*Congratulations!* You now have a set of Docker containers running, which can be updated and configured with editing a simple *YAML* file and doing a `git push`.

## Up next

This solution is OK to run a few applications but doesn't scale very well. It's also not super reliable, given that you have everything on a single server, if that goes down, nothing is accessible anymore.

In the next part of the [Home Lab](https://blog.viktoradam.net/tag/home-lab/) series I'll show a way to build on what we have here and expand the setup to multiple servers. We will keep the easy configuration and the continuous deployments but we'll *hopefully* remove the single point of failure.

Check out the other posts in the series:

1. [Home Lab - Overview](TODO)
2. *Home Lab - Setting up for Docker*
