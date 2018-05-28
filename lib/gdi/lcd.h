#ifndef __lcd_h
#define __lcd_h

#include <asm/types.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/erect.h>
#include "gpixmap.h"

#ifdef HAVE_GRAPHLCD
#include <glcdgraphics/bitmap.h>
#include <glcdgraphics/glcd.h>
#include <glcdgraphics/image.h>
#include <glcddrivers/config.h>
#include <glcddrivers/driver.h>
#include <glcddrivers/drivers.h>
#include <glcdgraphics/extformats.h>
#include <byteswap.h>
#endif

#ifdef NO_LCD
#include <lib/driver/vfd.h>
#endif

#define LCD_CONTRAST_MIN 0
#define LCD_CONTRAST_MAX 63
#define LCD_BRIGHTNESS_MIN 0
#define LCD_BRIGHTNESS_MAX 255

class eLCD
{
#ifdef SWIG
	eLCD();
	~eLCD();
#else
protected:
	eSize res;
	int lcd_type;
	unsigned char *_buffer;
	int lcdfd;
	int _stride;
	int locked;
	static eLCD *instance;
	void setSize(int xres, int yres, int bpp);
#ifdef NO_LCD
	evfd *vfd;
#endif
#endif
public:
	static eLCD *getInstance();
	virtual int lock();
	virtual void unlock();
	virtual int islocked() { return locked; };
	virtual bool detected() { return lcdfd >= 0; };
	virtual int setLCDContrast(int contrast)=0;
	virtual int setLCDBrightness(int brightness)=0;
	virtual void setInverted( unsigned char )=0;
	virtual void setFlipped(bool)=0;
	virtual void dumpLCD(bool png=true)=0;
	virtual int waitVSync()=0;
	virtual bool isOled() const=0;
	int getLcdType() { return lcd_type; };
	virtual void setPalette(gUnmanagedSurface)=0;
#ifndef SWIG
	eLCD();
	virtual ~eLCD();
	uint8_t *buffer() { return (uint8_t*)_buffer; };
	int stride() { return _stride; };
	virtual eSize size() { return res; };
	virtual void update()=0;
#ifndef NO_LCD
#ifdef HAVE_TEXTLCD
	virtual void renderText(ePoint start, const char *text);
#endif
#else
	virtual void renderText(const char *text);
#endif
#endif
};

class eDBoxLCD: public eLCD
{
	unsigned char inverted;
	bool flipped;
#ifdef HAVE_GRAPHLCD
	GLCD::cDriver * lcd;
	GLCD::cBitmap * bitmap;
	int displayNumber;
	int depth;
	int width, height;
#endif
#ifdef SWIG
	eDBoxLCD();
	~eDBoxLCD();
#endif
public:
#ifndef SWIG
	eDBoxLCD();
	~eDBoxLCD();
#endif
	int setLCDContrast(int contrast);
	int setLCDBrightness(int brightness);
	void setInverted( unsigned char );
	void setFlipped(bool);
	void dumpLCD(bool);
	bool isOled() const { return !!lcd_type; };
	void setPalette(gUnmanagedSurface) {};
	void update();
	int waitVSync() { return 0; };
};

#endif
