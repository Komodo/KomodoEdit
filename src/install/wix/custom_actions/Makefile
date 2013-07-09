all: custom_actions.dll

OBJECTS = checkEmptyDir.o

custom_actions.dll: $(OBJECTS)
	link -nologo -debug -out:$@ -pdb:$(basename $@).pdb -dll -machine:x86 \
	    -subsystem:windows,5.01 $<

$(OBJECTS): %.o: %.cpp
	cl -nologo -c -Wall -DNDEBUG -Os -MT -Zi -Fd$(basename $@).pdb -Fo$@ \
	    -D_USING_V110_SDK71_ -wd4820 -wd4668 -c $<

clean:
	rm -f custom_actions.{dll,exp,ilk,lib,pdb}
	rm -f $(OBJECTS:.o={.o,.pdb})
