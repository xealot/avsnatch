import datetime
import time


def parse_date(date):
    if isinstance(date, basestring):
        date = int(date)
    gmtime = time.gmtime(date)
    return datetime.date(gmtime.tm_year, gmtime.tm_mon, gmtime.tm_mday)


class NZBSegment(object):
    def __init__(self, bytes, number, message_id, groups):
        self.bytes = int(bytes)
        self.number = int(number)
        self.message_id = message_id
        self.groups = groups


class NZBFile(object):
    def __init__(self, poster, date, subject, groups=None, segments=None):
        self.poster = poster
        self.date = parse_date(date)
        self.subject = subject
        self.groups = groups or []
        self.segments = segments or []
        self.bytes = 0

    def add_group(self, group):
        self.groups.append(group)

    def add_segment(self, segment):
        self.bytes += segment.bytes
        segment.file = self
        self.segments.append(segment)


class NZB(object):
    def __init__(self, subject, files=None):
        self.subject = subject
        self.files = files or []

    def add_files(self, *a):
        self.files.extend(a)


class BaseNZBParser(object):
    def parse(self, xml):
        raise NotImplementedError


class BaseETreeNZBParser(BaseNZBParser):
    def get_etree_iter(self, xml, et=None):
        raise NotImplementedError

    def parse(self, xml):
        context = self.get_etree_iter(xml)
        #files, current_file, current_segment = [], None, None

        ns = {'ns': 'http://www.newzbin.com/DTD/2003/nzb'}
        name = self.parsed.find(".//ns:head/ns:meta[@type='name']", namespaces=ns).text

        nzb = NZB(name)

        files = self.parsed.findall(".//ns:file", namespaces=ns)
        for f in files:
            groups = [i.text for i in f.findall('.//ns:group', namespaces=ns)]
            file = NZBFile(
                poster=f.attrib['poster'],
                date=f.attrib['date'],
                subject=f.attrib['subject'],
                groups=[f.text for f in f.findall('.//ns:group', namespaces=ns)]
            )
            for s in self.parsed.findall(".//ns:file/ns:segments/ns:segment", namespaces=ns):
                file.add_segment(NZBSegment(
                    bytes=s.attrib['bytes'],
                    number=s.attrib['number'],
                    message_id=s.text,
                    groups=groups
                ))
            nzb.add_files(file)

        return nzb

#        for event, elem in context:
#            tag = elem.tag  #:TODO: Sorta hacked out namespaces here, might be a better way.
#            if event == "start":
#                # If it's an NZBFile, create an object so that we can add the
#                # appropriate stuff to it.
#                if tag in ("{http://www.newzbin.com/DTD/2003/nzb}file", 'file'):
#                    current_file = NZBFile(
#                        poster = elem.attrib['poster'],
#                        date = elem.attrib['date'],
#                        subject = elem.attrib['subject']
#                    )
#
#            elif event == "end":
#                if tag in ("{http://www.newzbin.com/DTD/2003/nzb}file", 'file'):
#                    files.append(current_file)
#
#                elif tag in ("{http://www.newzbin.com/DTD/2003/nzb}group", 'group'):
#                    current_file.add_group(elem.text)
#
#                elif tag in ("{http://www.newzbin.com/DTD/2003/nzb}segment", 'segment'):
#                    current_file.add_segment(
#                        NZBSegment(
#                            bytes = elem.attrib['bytes'],
#                            number = elem.attrib['number'],
#                            message_id = elem.text,
#                            groups = current_file.groups
#                        )
#                    )
#                # Clear the element, we don't need it any more.
#                elem.clear()
#        return files
