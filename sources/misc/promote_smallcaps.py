#!/usr/bin/env python3
# Take a UFO font with smallcaps glyphs named like "a.sc", "hyphen.sc" and "promote" them to "a", "hyphen", receiving Unicode codepoint of "parent" glyph.

import glob
import os
import re
import shutil
import sys

# You can ignore certain glyphs tagged ".sc" for removal here. For example, even in an SC default font, hyphen.sc is still useful. Use .glif filenames
IGNORE_LIST = ["idotaccent.sc.glif", "hyphen.sc.glif"]

_, ufo = sys.argv

# First, figure out where we are and what we're working on.

assert re.findall('\.ufo[23]?/*$', ufo, re.IGNORECASE), "argument must be a UFO"

if ufo[-1] == os.sep:
    ufo = ufo[:-1]

if "-" in ufo[ufo.rindex(os.sep)+1:]:
    familyname = ufo[ufo.rindex(os.sep)+1:ufo.rindex("-")]
    stylename = ufo[ufo.rindex("-")+1:ufo.rindex(".")]
else:
    familyname = ufo[ufo.rindex(os.sep)+1:ufo.rindex(".")]
    stylename = None

sc_ufo = ufo.replace(familyname, familyname+"SC")

shutil.rmtree(sc_ufo, ignore_errors=True)
shutil.copytree(ufo, sc_ufo)

glyphsdir = sc_ufo + os.sep + "glyphs"
dirglob = glyphsdir + os.sep + "*"

# Collect all the smallcap glyphs except those asked not to be above

sc_glyphs = list()

for f in glob.glob(dirglob):
    fn = f[f.rindex(os.sep)+1:]
    if not fn.endswith(".sc.glif") or fn in IGNORE_LIST:
        continue
    sc_glyphs.append(fn)

# Open all the XML glyph files and reorganize .sc glyphs to refer to their parents and have the components their parents would
# This deletes the parent glyphs

from xml.etree import ElementTree as ET
from io import BytesIO

for g in sc_glyphs:
    non_sc_fn = glyphsdir + os.sep + g.removesuffix(".sc.glif") + ".glif"
    sc_fn = glyphsdir + os.sep + g

    with open(non_sc_fn) as f:
        non_sc_xml = ET.ElementTree(file=f)
    
    unich = chr(int(non_sc_xml.getroot().find("unicode").get("hex"), 16))

    with open(sc_fn) as f:
        sc_xml = ET.ElementTree(file=f)

    if unicode_el := sc_xml.getroot().find("unicode") is None:
        unich_sc = -1
    else:
        unich_sc = chr(int(unicode_el.get("hex"), 16))

    output = open(non_sc_fn, "wb+")

    sc_xml.getroot().attrib["name"] = sc_xml.getroot().attrib["name"].removesuffix(".sc")

    new_unicode_el = ET.Element("unicode")
    new_unicode_el.set("hex", "{:04X}".format(ord(unich)))
    sc_xml.getroot().insert(0, new_unicode_el)

    for child in sc_xml.getroot().find("outline").iter():
        if not child.tag == "component": continue
        if child.tag == "component" and "base" in child.attrib and child.attrib["base"].endswith(".sc"):
            child.attrib["base"] = child.attrib["base"].removesuffix(".sc")

    sc_xml.write(output, xml_declaration=True)

    os.unlink(sc_fn)

# Open the glyph directory contents list, and remove all .sc's, as they've already overwritten their parents

import plistlib

plistf = glyphsdir + os.sep + "contents.plist"
sc_glyphs_sc = [g.removesuffix(".glif").replace("_","") for g in sc_glyphs]
sc_glyphs_nonsc = [g.removesuffix(".sc") for g in sc_glyphs_sc]

with open(plistf, "rb") as f:
    plistd = plistlib.load(f)

for key in list(plistd.keys()):
    if key in sc_glyphs_sc or key == "idotaccent.sc":
        del plistd[key]

with open(plistf, "wb+") as f:
    plistlib.dump(plistd, f)

# Massage the feature file

with open(glyphsdir + os.sep + ".." + os.sep + "features.fea") as f:
    fea = f.read()

import re

def nullify_if_nonsc(match):
    if match.group(0)[1:] in sc_glyphs_nonsc:
        return ""
    elif match.group(0).endswith(".sc"):
        return match.group(0).removesuffix(".sc")
    else:
        return match.group(0)

nfea = re.sub("\\\\[a-zA-Z0-9.-_]+", nullify_if_nonsc, fea)

for line in nfea.splitlines():
    if re.match("@[a-z_0-9]+ = \[ +\];", line):
        print(line)

with open(glyphsdir + os.sep + ".." + os.sep + "features.fea", "w+") as f:
    f.write(nfea)

# :g/sub \+by/d
# :g/sub.*by \\idotaccent/d
# :%s/\\idotaccent//g
