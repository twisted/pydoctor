from lxml.html import document_fromstring, tostring
import glob
import traceback
import re
import sys

errors = []

def elements_equal(e1, e2):
    if e1.tag != e2.tag:
        errors.append((tostring(e1), tostring(e2)))
        return False
    if e1.text != e2.text:
        errors.append((tostring(e1), tostring(e2)))
        return False
    if e1.tail != e2.tail:
        if re.sub("\s+", " ", e1.tail) != re.sub("\s+", " ", e2.tail):
            errors.append((repr(e1.tail), repr(e2.tail)))
            return False
    if e1.attrib != e2.attrib:
        errors.append((tostring(e1), tostring(e2)))
        return False
    if len(e1) != len(e2):
        errors.append((tostring(e1), tostring(e2)))
        return False
    return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))

def main():

    errored = False
    files = glob.glob("apidocs/*.html")

    for filename in files:

        with open(filename, 'rb') as f:
            py2 = f.read()

        with open(filename.replace('apidocs/', 'apidocs3/'), 'rb') as f:
            py3 = f.read()

        doc2 = document_fromstring(py2)
        doc3 = document_fromstring(py3)

        try:
            eq = elements_equal(doc2, doc3)
        except Exception as e:
            print("ERROR DECODING", filename.replace('apidocs/', ''))
            traceback.print_exc()
            eq = False

        if not eq:
            errored = True
            print("ERROR IN", filename.replace('apidocs/', ''), ":")
            for err in errors:
                print("PY2:", err[0])
                print("PY3:", err[1])

        errors.clear()

    if errored:
        sys.exit(1)

if __name__ == "__main__":
    main()