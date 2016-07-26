MODULE = mySpace
SRC = $(MODULE).py iot.py

mySpace.zip:	$(SRC)
		zip $(MODULE).zip $(SRC)

install:	$(MODULE).zip
		rm -f *~
		git add Makefile $(SRC) $(MODULE).zip
		git commit -m "latest changes"
		git push -u origin master

clean:		
		rm -f $(MODULE).zip
		rm -f *~
