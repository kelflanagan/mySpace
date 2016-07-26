mySpace.zip:	mySpace.py iot.py
		zip mySpace.zip mySPace.py iot.py

install:	mySpace.zip
		rm -f *~
		git add Makefile *.py *.zip
		git commit -m "latest changes"
		git push -u origin master
