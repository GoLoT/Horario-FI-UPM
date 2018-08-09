# -*- coding: utf-8 -*

import xml.etree.ElementTree as ET
import sys
import re

#Compiled regexes to find weekday/time/group texts
mon_re = re.compile(r"lunes", re.IGNORECASE)
tue_re = re.compile(r"martes", re.IGNORECASE)
wed_re = re.compile(r"mi.rcoles", re.IGNORECASE)
thu_re = re.compile(r"jueves", re.IGNORECASE)
fri_re = re.compile(r"viernes", re.IGNORECASE)
time_re = re.compile(r"(\d{1,2}:\d{1,2}).(\d{1,2}:\d{1,2})", re.IGNORECASE)
group_re = re.compile(r"grupo ([\w-]+)", re.IGNORECASE)

result = {}

#Check that we get at least 1 argument
if len(sys.argv) < 2:
    sys.exit("No XML file specified")

def getDayAbrev(i):
    if i == 0:
        return "mon"
    elif i == 1:
        return "tue"
    elif i == 2:
        return "wed"
    elif i == 3:
        return "thu"
    elif i == 4:
        return "fri"
    else:
        return None

def processRoot(root):
    for child in root:
        if child.tag == "page":
            processPage(child)

def testOverlap(box1, box2):
    return box1["top"] + box1["height"] >= box2["top"] and box2["top"] + box2["height"] >= box1["top"] and box1["left"] + box1["width"] >= box2["left"] and box2["left"] + box2["width"] >= box1["left"]

def processPage(page):
    #Starting values
    day_boxes = [0, 0, 0, 0, 0, 0]
    time_defs = []
    text_buffer = []
    groups = []
    #Loop through all children of this page
    for child in page:
        #Process all text nodes and compare against regexes
        if child.tag == "text" and child.text is not None:
            if mon_re.match(child.text):
                day_boxes[0] = {"top": int(child.attrib["top"]), "left": int(child.attrib["left"]), "height": int(child.attrib["height"]), "width": 80000}
            elif tue_re.match(child.text):
                day_boxes[1] = {"top": int(child.attrib["top"]), "left": int(child.attrib["left"]), "height": int(child.attrib["height"]), "width": 80000}
            elif wed_re.match(child.text):
                day_boxes[2] = {"top": int(child.attrib["top"]), "left": int(child.attrib["left"]), "height": int(child.attrib["height"]), "width": 80000}
            elif thu_re.match(child.text):
                day_boxes[3] = {"top": int(child.attrib["top"]), "left": int(child.attrib["left"]), "height": int(child.attrib["height"]), "width": 80000}
            elif fri_re.match(child.text):
                day_boxes[4] = {"top": int(child.attrib["top"]), "left": int(child.attrib["left"]), "height": int(child.attrib["height"]), "width": 80000}
            else:
                time = time_re.match(child.text)
                if time:
                    time_defs.append((time.group(1), time.group(2), {"top": int(child.attrib["top"]), "left": int(child.attrib["left"]), "height": 80000, "width": int(child.attrib["width"])}))
                else:
                    #If text wasn't a weekday or a time, save it for later processing
                    text_buffer.append(child)
        else:
            #Process non-text nodes to see if they are nodes that contain text
            #going 1 level deep (i.e. find bold text)
            if child.tag == "text":
                text_buffer.append(child)
            text = None
            if child.text is not None:
                text = child.text
            else:
                for content in child:
                    if content.text is not None:
                        text = content.text
            #If we found text we check against more regex
            if text is not None:
                #Check if it defines a group
                if group_re.match(text):
                    group = group_re.match(text)
                    groups.append((group.group(1), ""))
                    groups = list(set(groups))
                #else:
                #    print("Other: ", text)
    print("Times: ", time_defs)
    print("Groups: ", groups)
    print("Days: ", day_boxes)
    prev = None
    current = {}
    subject_texts = []
    #Loop through all possible subjects
    for elem in text_buffer:
        #Check if the text is inside the table
        if elem.attrib["top"] < day_boxes[0]["top"] or int(elem.attrib["top"]) > (day_boxes[4]["top"] + day_boxes[4]["height"]*2):
            #Out of table
            continue
        if prev is not None:
            #Check if this text is part of the previous text (multiline text)
            dif = int(prev.attrib["height"]) + int(prev.attrib["top"]) - int(elem.attrib["top"])
            if dif < 2 and dif > -2:
                #If it is, we append it
                if elem.text is not None:
                    current["text"] = current["text"] + elem.text
                current["height"] = max(int(elem.attrib["top"]) + int(elem.attrib["height"]), current["top"]+current["height"]) - min(int(elem.attrib["top"]), current["top"])
                current["width"] = max(int(elem.attrib["left"]) + int(elem.attrib["width"]), current["left"]+current["width"]) - min(int(elem.attrib["left"]), current["left"])
            else:
                #If it isn't, we create a new node
                subject_texts.append(current)
                current = {"top": int(elem.attrib["top"]), "height": int(elem.attrib["height"]), "width": int(elem.attrib["width"]), "left": int(elem.attrib["left"]), "text": elem.text}
        else:
            #First iteration, create a new node
            current = {"top": int(elem.attrib["top"]), "height": int(elem.attrib["height"]), "width": int(elem.attrib["width"]), "left": int(elem.attrib["left"]), "text": elem.text}
        prev = elem
    subject_texts.append(current)

    #Init groups in result variable
    for g in groups:
        result[g[0]] = {}
        for i in range(0,5):
            result[g[0]][getDayAbrev(i)] = []

    for subj in subject_texts:
        if subj["text"] is None:
            continue
        #Find day
        day = None
        times = []
        for i in range(0,5):
            if testOverlap(subj, day_boxes[i]):
                day = getDayAbrev(i)
                break
        if day is None:
            print("ERROR: Day can't be calculated", subj)
            continue
        #Find time
        tries = 0
        #Widen the bounding box each iteration to try to overlap time labels if no overlap occurs
        while len(times) < 1 and tries < 5:
            subj["left"] = subj["left"] - 10
            subj["width"] = subj["width"] + 20
            for t in time_defs:
                if testOverlap(subj, t[2]):
                    times.append(t)
            tries = tries + 1
        if len(times) < 1:
            print("ERROR: Time can't be calculated", subj)
            continue
        #TODO: Use RegExes to translate subject names to subject IDs
        start_time = times[0][0]
        end_time = times[-1][1]
        for g in groups:
            #TODO: Proper JSON formatting
            result[g[0]][getDayAbrev(i)].append((subj["text"], start_time + " - " + end_time))


tree = ET.parse(sys.argv[1])
root = tree.getroot()

processRoot(root)
print(result)

