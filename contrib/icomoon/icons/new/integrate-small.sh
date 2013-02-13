#!/bin/bash

for i in `ls | grep .svg`
do
	rsvg-convert $i -w 14 -h 14 -o `echo "../png/14px/$i" | sed -e 's/svg$/png/'`
	rsvg-convert $i -w 28 -h 28 -o `echo "../png/28px/$i" | sed -e 's/svg$/png/'`
	mv $i '../svg/'
done

