# Build Profiler

## How to use

#### Generating package orders before build

```
./bsr/bsr \
    preview \
    -s [Source Root] \
    -a [Architecture] \
    -r [Reference Snapshot URL] \
    --criticalsort --depsnumbersort
```

#### Generating build reports

```
./bsr/bsr \
    report \
    -s [Source Root] \
    -b [GBS Build Root] \
    -a [Architecture] \
    -r [Reference Snapshot URL] \
    --criticalsort --depsnumbersort
```


## Available features

### Build Overview

- Overview information.



### Critical Build Path

- It shows the package order with the longest build time during the build step.



### Dependency Graph

- This graph shows all or part of the package's relationship to each other. (Dependency/Reverse dependency)



### Build Timeline Heatmap

- This chart shows the distribution of build times for the entire package.



### Thread Concurrency in Time With CPU Utilization

- This graph shows the number of threads running at the same time during the build and CPU Utilizations.



### Build Time Diff

- This graph shows the difference in build time from previous builds by package.

