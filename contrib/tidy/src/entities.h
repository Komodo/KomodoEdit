#ifndef __ENTITIES_H__
#define __ENTITIES_H__

/* entities.h -- recognize character entities

  (c) 1998-2003 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: hoehrmann $ 
    $Date: 2003/05/25 03:22:20 $ 
    $Revision: 1.6 $ 

*/

#include "forward.h"

/* entity starting with "&" returns zero on error */
uint    EntityCode( ctmbstr name, uint versions );
ctmbstr EntityName( uint charCode, uint versions );
Bool    EntityInfo( ctmbstr name, Bool isXml, uint* code, uint* versions );

#endif /* __ENTITIES_H__ */
