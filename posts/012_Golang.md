# Go explore

Tales of adventures in Goland, one month in. *sed -i 's/land/lang/'*

I always wanted to give Go a Go, since a long time aGo. *(ok, I'll stop)* I wanted to see what all the hype is about, and how could I use it in my [Home lab](TODO). I thought it might be a good fit there, given I run it on small, resource-constrained devices, so the smaller I can get my Docker images, the better. I was also hoping to shave off some of the overall CPU and memory usage by writing apps in Go, instead of Python or Java. Plus, learning a new programming language is fun!

## Where to begin?

A good few years ago, I started learning Python by going through the official documentation on [docs.python.org](TODO), and I found it a good, comprehensive introduction to the basics of the core library. With Go, I took a similar approach. I went on [tour.golang.com](TODO), to get a feel of what is common with other languages I know, what is different, or something that is unique to this language (for me at least).

Next, I needed some IDE to start playing with the language on my developer machines. I like [JetBrains](TODO)' IDEs very much, and I have read some news about their [Goland](TODO) already, so it was time to have a look at it. I'm not a huge fan of installing SDKs, frameworks, libraries, IDEs, etc. on the host itself, because it's hard to keep it tidy, there are issues with updates and such, we're much better off dealing with these in a container you can easily throw away and start over. I quickly wrote a [Dockerfile](TODO GitHub) for [rycus86/goland](TODO), mostly based on what I already had for [PyCharm](TODO) and [IntelliJ](TODO), built the new image locally, and we were in business. I started with release candidates for *2018.1*, so I could use them for a few weeks, until the release finally came out, then I just bought the license straight away, by then I was convinced it's worth it. I use it like this at home:

```shell
$ TODO docker run ...
```

I have an alternative dev environment prepared on my work MacBook I also use while travelling by train, this is based on the [golang:1.10](TODO) official image, with [vim](TODO) added on top, plus some utilities I often use, like *git*, *curl*, etc. This might feel a bit more difficult than using a visual IDE, but Go has wonderful and useful error messages, and you can always look up library types and functions by opening the sources that comes with the installation.

## First impressions

Installing a binary distribution (TODO name?) of a specific Go release is not as trivial as I would like it to be. It's fine if you start with the official images, or maybe if you install it with a package manager, but otherwise you have to set up a few environment variables to have it working properly, which is not easy if you're looking at this for the first time. I'm pretty sure I still haven't got this part right.

Dependency management is... interesting. Gave `go get` a quick spin, probably not the right way though, then had a quick look what else is there, and settled on `dep` for now. It looks easy enough, and it just works most of the time. I have run into some issues with it already, so it may not be the final tool I end up with.

The Go syntax overall looks pretty good to me. Getting the hang of writing the type on the right side of the variable was easier than I expected, `var` and `const` makes sense, and `func` is fine too after all those `def`s. The `=`/`:=` thing is a bit annoying for now, but OK. The `for` loop felt a bit weird, but getting used to it now, and by this I mean, I can no longer write a syntactically correct one anymore in either Go, Python or Java on the first try... Is it:

- `for (int idx = 0; idx < length; idx++) { }`
- `for (final X x : xs) { }` or
- `for x in xs:`
- `for idx, x in enumerate(xs):`
- `for key, value in d.items():` or perhaps
- `for _, x := range xs { }`
- `for key, value := range d { }` or...
- `for { }`

So yeah, who knows... Anyway, I had to realise, I didn't really miss pointers at all, I'd be perfectly happy passing everything as references instead of values. But enough of this complaining, there are loads of cool things I like about Go immediately.

Goroutines (TODO one word?) are awesome. You need something done soon-ish, does not need to block the current thread, and don't necessarily care about the result? Just `go whatEver()`. Channels are also pretty neat if you do need some results, or maybe need the items produced by the goroutine (TODO) one-by-one. Sounds like a super-lightweight (code-wise at least) queue, that you can simply `ch<- add` (TODO) items to, or `take := <-ch` them from it. And you get a `panic` if something goes wrong, instead of just losing threads forever at runtime due to a deadlock. (TODO build-time check?)

Splitting up a package into multiple files is also nice, something that could come in handy in Python sometimes.

> TODO gofmt, interface implementation (name?), function reference (without a class like Java), module init(), http client/server, testing, httptest

