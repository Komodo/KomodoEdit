#include <nsStringGlue.h>
#include "SciMozEvents.h"

NS_DEFINE_STATIC_IID_ACCESSOR(SciMozEventsWrapper, SCIMOZEVENTSWRAPPER_IID)
nsresult SciMozEventsWrapper::Invoke(const char* aMethodName,  const NPVariant *args, uint32_t argCount) {
	NPVariant result = { NPVariantType_Void };
	bool success = NPN_Invoke(mInstance,
				  mWrappee,
				  NPN_GetStringIdentifier(aMethodName),
				  args,
				  argCount,
				  &result);
	return success ? NS_OK : NS_ERROR_FAILURE;
}
NS_IMETHODIMP SciMozEventsWrapper::OnCharAdded(PRInt32 ch) {
	NPVariant arg;
	INT32_TO_NPVARIANT(ch, arg);
	return Invoke("onCharAdded", &arg, 1);
}
NS_IMETHODIMP SciMozEventsWrapper::OnSavePointReached() {
	return Invoke("onSavePointReached", nullptr, 0);
}
NS_IMETHODIMP SciMozEventsWrapper::OnSavePointLeft() {
	return Invoke("onSavePointLeft", nullptr, 0);
}
NS_IMETHODIMP SciMozEventsWrapper::OnDoubleClick() {
	return Invoke("onDoubleClick", nullptr, 0);
}
NS_IMETHODIMP SciMozEventsWrapper::OnUpdateUI(int updated,
					      int horizScrollPageIncrement)
{
	NPVariant args[2];
	INT32_TO_NPVARIANT(updated, args[0]);
	INT32_TO_NPVARIANT(horizScrollPageIncrement, args[1]);
	return Invoke("onUpdateUI", args, 2);
}
NS_IMETHODIMP SciMozEventsWrapper::OnModified(PRInt32 position,
					      PRInt32 modificationType,
					      const nsAString & text,
					      PRUint32 length,
					      PRInt32 linesAdded,
					      PRInt32 line,
					      PRInt32 foldLevelNow,
					      PRInt32 foldLevelPrev)
{
	NS_ConvertUTF16toUTF8 textUtf8(text);
	NPVariant args[8];
	INT32_TO_NPVARIANT(position, args[0]);
	INT32_TO_NPVARIANT(modificationType, args[1]);
	STRINGN_TO_NPVARIANT(textUtf8.get(), textUtf8.Length(), args[2]);
	INT32_TO_NPVARIANT(length, args[3]);
	INT32_TO_NPVARIANT(linesAdded, args[4]);
	INT32_TO_NPVARIANT(line, args[5]);
	INT32_TO_NPVARIANT(foldLevelNow, args[6]);
	INT32_TO_NPVARIANT(foldLevelPrev, args[7]);
	return Invoke("onModified", args, 8);
}
NS_IMETHODIMP SciMozEventsWrapper::OnMarginClick(PRInt32 modifiers, PRInt32 position, PRInt32 margin) {
	NPVariant args[3];
	INT32_TO_NPVARIANT(modifiers, args[0]);
	INT32_TO_NPVARIANT(position, args[1]);
	INT32_TO_NPVARIANT(margin, args[2]);
	return Invoke("onMarginClick", args, 3);
}
NS_IMETHODIMP SciMozEventsWrapper::OnZoom() {
	return Invoke("onZoom", nullptr, 0);
}
NS_IMETHODIMP SciMozEventsWrapper::OnHotSpotDoubleClick(PRInt32 position, PRInt32 modifiers) {
	NPVariant args[2];
	INT32_TO_NPVARIANT(position, args[0]);
	INT32_TO_NPVARIANT(modifiers, args[1]);
	return Invoke("onHotSpotDoubleClick", args, 2);
}
NS_IMETHODIMP SciMozEventsWrapper::OnDwellStart(PRInt32 position, PRInt32 x, PRInt32 y) {
	NPVariant args[3];
	INT32_TO_NPVARIANT(position, args[0]);
	INT32_TO_NPVARIANT(x, args[1]);
	INT32_TO_NPVARIANT(y, args[2]);
	return Invoke("onDwellStart", args, 3);
}
NS_IMETHODIMP SciMozEventsWrapper::OnDwellEnd(PRInt32 position, PRInt32 x, PRInt32 y) {
	NPVariant args[3];
	INT32_TO_NPVARIANT(position, args[0]);
	INT32_TO_NPVARIANT(x, args[1]);
	INT32_TO_NPVARIANT(y, args[2]);
	return Invoke("onDwellEnd", args, 3);
}
NS_IMETHODIMP SciMozEventsWrapper::OnOtherNotification(PRInt32 notificationType,
						       PRInt32 position,
					               const nsAString & text,
						       PRInt32 modifiers) {
	NS_ConvertUTF16toUTF8 textUtf8(text);
	NPVariant args[4];
	INT32_TO_NPVARIANT(notificationType, args[0]);
	INT32_TO_NPVARIANT(position, args[1]);
	STRINGN_TO_NPVARIANT(textUtf8.get(), textUtf8.Length(), args[2]);
	INT32_TO_NPVARIANT(modifiers, args[3]);
	return Invoke("onOtherNotification", args, 4);
}
NS_IMETHODIMP SciMozEventsWrapper::OnCommandUpdate(const char *commandset) {
	NPVariant arg;
	STRINGN_TO_NPVARIANT(commandset, strlen(commandset), arg);
	return Invoke("onCommandUpdate", &arg, 1);
}

// Mozilla 31 code base changed - dropping NS_IMPL_ISUPPORTSN, so we support
// both till everyone updates their mozilla builds.
#ifdef NS_IMPL_ISUPPORTS2
NS_IMPL_ISUPPORTS2(SciMozEventsWrapper, SciMozEventsWrapper, ISciMozEvents)
#else
NS_IMPL_ISUPPORTS(SciMozEventsWrapper, SciMozEventsWrapper, ISciMozEvents)
#endif
