#!/bin/sh

# render the frames
blender -b -P render.py

# convert to mp4 videos
for i in render/frames/*/*; do
    dataset=$(basename $(dirname $i))
    name=$(basename $i)
    mkdir -p "render/videos/$dataset"
    ffmpeg -y -r 24 -f image2 -s 800x600 -i "$i/%04d.png" -vcodec libx264 -crf 25 -pix_fmt yuv420p "render/videos/$dataset/$name.mp4"
done
