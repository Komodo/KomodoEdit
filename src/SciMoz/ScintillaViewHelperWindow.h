/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/* Copyright (c) 2000-2012 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information.

   Some code adapted from FireBreath
   (https://github.com/firebreath/), used under the BSD License
*/

@interface ScintillaViewHelperWindow : NSPanel {
    BOOL isActive;
}
- (BOOL)worksWhenModal;
- (void)setIsActive:(BOOL)active;
@end
