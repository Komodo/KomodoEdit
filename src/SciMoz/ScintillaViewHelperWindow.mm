/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/* Copyright (c) 2000-2012 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information.

   Some code adapted from FireBreath
   (https://github.com/firebreath/), used under the BSD License
*/

@implementation ScintillaViewHelperWindow

- (void)setIsActive:(BOOL)active
{
    isActive = active;
}

- (BOOL)worksWhenModal
{
    return YES;
}

- (BOOL)canBecomeKeyWindow
{
    return isActive;
}

- (BOOL)isKeyWindow
{
    return isActive;
}

- (BOOL)acceptsMouseMovedEvents
{
    return YES;
}

- (BOOL)ignoresMouseEvents
{
    return NO;
}

@end
