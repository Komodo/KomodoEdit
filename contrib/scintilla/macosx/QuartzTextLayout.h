/*
 *  QuartzTextLayout.h
 *  wtf
 *
 *  Created by Evan Jones on Wed Oct 02 2002.
 *  Copyright (c) 2002 __MyCompanyName__. All rights reserved.
 *
 */

#ifndef _QUARTZ_TEXT_LAYOUT_H
#define _QUARTZ_TEXT_LAYOUT_H

#include <Carbon/Carbon.h>

#include "QuartzTextStyle.h"

class QuartzTextLayout
{
public:
    /** Create a text layout for drawing on the specified context. */
    QuartzTextLayout( CGContextRef context ) : layout( NULL ), unicode_string( NULL ), unicode_length( 0 )
    {
        gc = context;

        OSStatus err;
        err = ATSUCreateTextLayout( &layout );
        assert( err == noErr && layout != NULL );

        setControl( kATSUCGContextTag, sizeof( gc ), &gc );

        /*ATSUAttributeTag tag = kATSULineLayoutOptionsTag;
        ByteCount size = sizeof( ATSLineLayoutOptions );
        ATSLineLayoutOptions rendering = kATSLineHasNoOpticalAlignment; // kATSLineUseDeviceMetrics; | kATSLineFractDisable | kATSLineUseQDRendering
        ATSUAttributeValuePtr valuePtr = &rendering;
        err = ATSUSetLayoutControls( layout, 1, &tag, &size, &valuePtr );
        assert( err == noErr );*/
    }

    ~QuartzTextLayout()
    {
        assert( layout != NULL );
        ATSUDisposeTextLayout( layout );
        layout = NULL;

        if ( unicode_string != NULL )
        {
            delete[] unicode_string;
            unicode_string = NULL;
            unicode_length = 0;
        }
    }

    /** Assign a string to the text layout object. */
    // TODO: Create a UTF8 version
    // TODO: Optimise the ASCII version by not copying so much
    OSStatus setText( const UInt8* buffer, size_t byteLength, CFStringEncoding encoding )
    {
        assert( buffer != NULL && byteLength > 0 );
        
        CFStringRef str = CFStringCreateWithBytes( NULL, buffer, byteLength, encoding, false );
        if (!str)
            return -1;

        unicode_length = CFStringGetLength( str );
        unicode_string = new UniChar[ unicode_length ];
        CFStringGetCharacters( str, CFRangeMake( 0, unicode_length ), unicode_string );

        CFRelease( str );
        str = NULL;

        OSStatus err;
        err = ATSUSetTextPointerLocation( layout, unicode_string, kATSUFromTextBeginning, kATSUToTextEnd, unicode_length );
        if( err != noErr ) return err;

        // Turn on the default font fallbacks
        return ATSUSetTransientFontMatching( layout, true );
    }

    /** Apply the specified text style on the entire range of text. */
    void setStyle( const QuartzTextStyle& style )
    {
        OSStatus err;
        err = ATSUSetRunStyle( layout, style.getATSUStyle(), kATSUFromTextBeginning, kATSUToTextEnd );
        assert( err == noErr );
    }

    /** Draw the text layout into the current CGContext at the specified position, flipping the CGContext's Y axis if required.
    * @param x The x axis position to draw the baseline in the current CGContext.
    * @param y The y axis position to draw the baseline in the current CGContext.
    * @param flipTextYAxis If true, the CGContext's Y axis will be flipped before drawing the text, and restored afterwards. Use this when drawing in an HIView's CGContext, where the origin is the top left corner. */
    void draw( float x, float y, bool flipTextYAxis = false )
    {
        if ( flipTextYAxis )
        {
            CGContextSaveGState( gc );
            CGContextScaleCTM( gc, 1.0, -1.0 );
            y = -y;
        }
        
        OSStatus err;
        err = ATSUDrawText( layout, kATSUFromTextBeginning, kATSUToTextEnd, X2Fix( x ), X2Fix( y ) );
        assert( err == noErr );

        if ( flipTextYAxis ) CGContextRestoreGState( gc );
    }

    /** Sets a single text layout control on the ATSUTextLayout object.
    * @param tag The control to set.
    * @param size The size of the parameter pointed to by value.
    * @param value A pointer to the new value for the control.
    */
    void setControl( ATSUAttributeTag tag, ByteCount size, ATSUAttributeValuePtr value )
    {
        OSStatus err;
        err = ATSUSetLayoutControls( layout, 1, &tag, &size, &value );
        assert( noErr == err );
    }

    ATSUTextLayout getLayout() {
        return layout;
    }

private:
    ATSUTextLayout layout;
    UniChar* unicode_string;
    int unicode_length;
    CGContextRef gc;
};

#endif
