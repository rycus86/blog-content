# Gating on README updates

If you're like me, you perhaps also often forget to update your README files in the heat of coding up the latest features in your projects. How can we make sure that it happens in a timely manner? Add unit tests for it, and make your build fail!

## TODO subtitle

I struggle a lot with this on my projects. I work hard on implementing some new functionality, write the tests for it, then start fighting with the build issues on Travis. Somewhere in this process, I should add a sentence or a paragraph on the new feature to the README, but it's easy to miss it. When I finally do remember to do it, I just add a task for it to my Trello board, then either get around to do it eventually, or it slowly wastes away in the TODO column, virtually every new idea coming on the board in front of it.

I have a few projects that need to deal with configuration files, and new functionality usually involves supporting new properties in the config. Without the need for a full-blown documentation site, or even a Wiki, I tend to just list out all these in the project README, along with some explanation, default values, maybe examples. I also sometimes include the command line help output the app produces. Most argument parsers allow you to define help strings with the recognized options, like [argparse](TODO) in Python or [flags](TODO) in Go, so it makes sense to reuse their nicely formatted output.

Similarly to the help string, I thought it would be nice to generate a documentation block based on the configuration options *currently* supported by the project, so I decided to look into this. Once you can generate these outputs, it's much easier to just copy-paste it in the right place in the README. But wait, there's more! If you did this much, you can also check, programmatically, if you have actually put the updated output in the documentation.

Let me walk you through a simple implementation I use on a new app I'm working on.

## Command line usage

> TODO

## Configuration properties

> TODO

