#!/bin/bash

for i in `ls | grep .svg`
do
	rsvg-convert $i -w 16 -h 16 -o `echo "../png/16px/$i" | sed -e 's/svg$/png/'`
	rsvg-convert $i -w 32 -h 32 -o `echo "../png/32px/$i" | sed -e 's/svg$/png/'`
	mv $i '../svg/'
done

