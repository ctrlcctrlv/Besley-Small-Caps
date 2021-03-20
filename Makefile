assets/besley.png:
	sile assets/besley.sil && \
	cd assets && \
	pdf2svg besley.pdf besley2.svg && \
	svgclip.py besley2.svg -o besley2O.svg -m 50 && \
	convert -density 200 besley2O.svg besley.png && \
	rm besley2.svg besley2O.svg besley.pdf
