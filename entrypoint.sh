#!/bin/bash

args=("$@")
command="python /app/mpyl/__main__.py"

for arg in "${args[@]}"
do
    # Split the argument on spaces and iterate over the words
    for word in $arg
    do
        command="$command \"$word\""
    done
done

# Execute the command
eval "$command"
