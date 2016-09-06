MODULE = mySpace
SRC = $(MODULE).py aws.py github.py
m=latest incremental changes

$(MODULE).zip:	$(SRC)
		zip $(MODULE).zip $(SRC)

commit:		$(MODULE).zip
		rm -f *~
		git add Makefile $(SRC) $(MODULE).zip
		git commit -m "$(m)" 
		git push -u origin master

clean:		
		rm -f $(MODULE).zip
		rm -f *~ *.pyc
