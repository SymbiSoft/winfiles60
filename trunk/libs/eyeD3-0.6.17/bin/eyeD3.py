#!/usr/bin/env python
################################################################################
#  Copyright (C) 2002-2008  Travis Shirk <travis@pobox.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################
import os, sys, math, locale;
import optparse;
from optparse import *;
from stat import *;
try:
   from eyeD3 import *;
   from eyeD3.tag import *;
   from eyeD3.frames import *;
   from eyeD3.utils import *;
except ImportError:
   # For development
   sys.path.append("../src");
   from eyeD3 import *;
   from eyeD3.tag import *;
   from eyeD3.frames import *;
   from eyeD3.utils import *;
ENCODING = locale.getpreferredencoding();


class ConsoleColors(dict):
   use = 1;

   def __init__(self):
      self["normal"]  = chr(0x1b) + "[0m";
      self["header"]  = chr(0x1b) + "[32m";
      self["warning"] = chr(0x1b) + "[33m";
      self["error"]   = chr(0x1b) + "[31m";
      self["bold"]    = chr(0x1b) + "[1m";

   def enabled(self, b):
      self.use = b;

   # Accessor override.
   def __getitem__(self, key):
      if self.use:
         return dict.__getitem__(self, key);
      else:
         return "";
colors = ConsoleColors();

class CommandException:
   msg = "";

   def __init__(self, msg):
      self.msg = msg;

   def __str__(self):
      return self.msg;


################################################################################
class OptionParserHelpFormatter(HelpFormatter):

    def __init__(self, indent_increment=2, max_help_position=24, width=79,
                 short_first=1):
        HelpFormatter.__init__ (self, indent_increment, max_help_position,
                                width, short_first);

    def format_usage(self, usage):
        return "\n%s  %s\n" % (self.format_heading("Usage"), usage);

    def format_heading(self, heading):
        return "%s\n%s\n" % (heading, "=-"[self.level] * len(heading));

    def format_option_strings(self, option):
        # This is the optparse implementation -- stolen, with spacing mods.
        if option.takes_value():
            metavar = option.metavar or option.dest.upper();
            short_opts = [sopt + " " + metavar for sopt in option._short_opts];
            long_opts = [lopt + "=" + metavar for lopt in option._long_opts];
        else:
            short_opts = option._short_opts;
            long_opts = option._long_opts;

        if self.short_first:
            opts = short_opts + long_opts;
        else:
            opts = long_opts + short_opts;
        return ", ".join(opts);

################################################################################
def getOptionParser():
   versionStr = \
"""eyeD3 %s (C) Copyright 2002-2008 %s
This program comes with ABSOLUTELY NO WARRANTY! See COPYING for details.
Run with --help/-h for usage information or see the man page 'eyeD3(1)'
""" % (eyeD3.eyeD3Version, eyeD3.eyeD3Maintainer)

   usageStr = "%prog [OPTS] file [file...]";
   helpFormatter = OptionParserHelpFormatter();
   optParser = OptionParser(usage=usageStr, version=versionStr,
                            formatter=helpFormatter);
   optParser.disable_interspersed_args();

   # Version options.
   versOpts = OptionGroup(optParser, "Tag Versions");
   versOpts.add_option("-1", "--v1", action="store_const",
                       const=eyeD3.ID3_V1, dest="tagVersion",
                       default=eyeD3.ID3_ANY_VERSION,
                       help="Only read/write ID3 v1.x tags. By default, "\
                             "v1.x tags are only read if there is not a v2.x "\
                             "tag.");
   versOpts.add_option("-2", "--v2", action="store_const",
                       const=eyeD3.ID3_V2, dest="tagVersion",
                       default=eyeD3.ID3_ANY_VERSION,
                       help="Only read/write ID3 v2.x tags.");
   versOpts.add_option("--to-v1.1", action="store_const",
                       const=eyeD3.ID3_V1_1, dest="convertVersion",
                       default=0,
                       help="Convert the file's tag to ID3 v1.1."\
                            " (Or 1.0 if there is no track number.)");
   versOpts.add_option("--to-v2.3", action="store_const",
                       const=eyeD3.ID3_V2_3, dest="convertVersion",
                       default=0,
                       help="Convert the file's tag to ID3 v2.3");
   versOpts.add_option("--to-v2.4", action="store_const",
                       const=eyeD3.ID3_V2_4, dest="convertVersion",
                       default=0,
                       help="Convert the file's tag to ID3 v2.4");
   optParser.add_option_group(versOpts);

   # Tag data options.
   grp1 = OptionGroup(optParser, "Tag Data");
   grp1.add_option("-a", "--artist", action="store", type="string",
                   dest="artist", metavar="STRING",
                   help="Set artist");
   grp1.add_option("-A", "--album", action="store", type="string",
                   dest="album", metavar="STRING",
                   help="Set album");
   grp1.add_option("-t", "--title", action="store", type="string",
                   dest="title", metavar="STRING",
                   help="Set title");
   grp1.add_option("-n", "--track", action="store", type="string",
                   dest="track", metavar="NUM",
                   help="Set track number");
   grp1.add_option("-N", "--track-total", action="store", type="string",
                   dest="track_total", metavar="NUM",
                   help="Set total number of tracks");
   grp1.add_option("-G", "--genre", action="store", type="string",
                   dest="genre", metavar="GENRE",
                   help="Set genre. The argument is a valid genre string or "\
                        "number.  See --list-genres");
   grp1.add_option("-Y", "--year", action="store", type="string",
                   dest="year", metavar="STRING",
                   help="Set a four digit year.");
   grp1.add_option("-c", "--comment", action="append", type="string",
                   dest="comments", metavar="[LANGUAGE]:[DESCRIPTION]:COMMENT",
                   help="Set comment");
   grp1.add_option("-L", "--lyrics", action="append", type="string",
                   dest="lyrics", metavar="[LANGUAGE]:[DESCRIPTION]:LYRICS",
                   help="Set lyrics");
   grp1.add_option("-p", "--publisher", action="store", type="string",
                   dest="publisher", metavar="STRING",
                   help="Set the publisher/label text");
   grp1.add_option("--remove-comments", action="store_true",
                   dest="remove_comments", help="Remove all comment frames.");
   grp1.add_option("--remove-lyrics", action="store_true",
                   dest="remove_lyrics", help="Remove all lyrics frames.");
   grp1.add_option("--add-image", action="append", type="string",
                   dest="images", metavar="IMG_PATH:TYPE[:DESCRIPTION]",
                   help="Add an image to the tag.  The description and type "\
                        "optional, but when used, both ':' delimiters must "\
                        "be present.  The type MUST be an string that "
                        "corresponds to one given with --list-image-types. "\
                        "If the IMG_PATH value is empty the APIC frame with "\
                        "TYPE is removed.");
   grp1.add_option("--remove-images", action="store_true",
                   dest="remove_images", help="Remove all image (APIC) frames.")
   grp1.add_option("--add-object", action="append", type="string",
                   dest="objects",
                   metavar="OBJ_PATH[:DESCRIPTION[:MIME-TYPE[:FILENAME]]",
                   help="Add an encapsulated object to the tag.  The "
                        "description "\
                        "and filename are optional, but when used, the ':' "\
                        "delimiters must be present.  If the OBJ_PATH value "\
                        "is empty the GEOB frame with DESCRIPTION is removed.");
   grp1.add_option("-i", "--write-images", type="string", action="store",
                   dest="writeImages", metavar="DIR", default=None,
                   help="Causes all attached images (APIC frames) to be "\
                        "written to the specified directory.");
   grp1.add_option("-o", "--write-objects", type="string", action="store",
                   dest="writeObjects", metavar="DIR", default=None,
                   help="Causes all attached objects (GEOB frames) to be "\
                        "written to the specified directory.");
   grp1.add_option("--set-text-frame", action="append", type="string",
                   dest="textFrames", metavar="FID:TEXT", default=[],
                   help="Set the value of a text frame.  To remove the "\
                        "frame, specify an empty value.  "\
                        "e.g., --set-text-frame=\"TDRC:\"");
   grp1.add_option("--set-user-text-frame", action="append", type="string",
                   dest="userTextFrames", metavar="DESC:TEXT", default=[],
                   help="Set the value of a user text frame (i.e., TXXX). "\
                        "To remove the frame, specify an empty value.  "\
                        "e.g., --set-user-text-frame=\"SomeDesc:\"");
   grp1.add_option("--set-url-frame", action="append", type="string",
                   dest="url_frames", metavar="FID:URL", default=[],
                   help="Set the value of a URL frame.  To remove the "\
                        "frame, specify an empty value.  "\
                        "e.g., --set-url-frame=\"WCOM:\"");
   grp1.add_option("--set-user-url-frame", action="append", type="string",
                   dest="user_url_frames", metavar="DESC:URL", default=[],
                   help="Set the value of a user URL frame (i.e., WXXX). "\
                        "To remove the frame, specify an empty value.  "\
                        "e.g., --set-user-url-frame=\"SomeDesc:\"");
   grp1.add_option("--play-count", action="store", type="string",
                   dest="play_count", metavar="[+]N", default=None,
                   help="If this argument value begins with '+' the tag's "\
                        "play count (PCNT) is incremented by N, otherwise the "\
                        "value is set to exactly N.");
   grp1.add_option("--bpm", action="store", type="string",
                   dest="bpm", metavar="N", default=None,
                   help="Set the beats per minute value.");
   grp1.add_option("--unique-file-id", action="append", type="string",
                   dest="unique_file_ids", metavar="OWNER_ID:ID", default=None,
                   help="Add a UFID frame.  If the ID arg is empty the UFID "\
                        "frame with OWNER_ID is removed.  An OWNER_ID MUST "\
                        "be specified.");
   grp1.add_option("--set-encoding", action="store", type="string",
                   dest="textEncoding", metavar="latin1|utf8|utf16-BE|utf16-LE",
                   default=None,
                   help="Set the encoding that is used for _all_ text "\
                        "frames. "\
                        "This only takes affect when the tag is updated as "\
                        "the "\
                        "result of a frame value being set with another "\
                        "option (e.g., --artist=) or --force-update is "\
                        "present.");
   grp1.add_option("--remove-v1", action="store_true",
                    dest="remove_v1", default=0,
                    help="Remove ID3 v1.x tag.");
   grp1.add_option("--remove-v2", action="store_true",
                    dest="remove_v2", default=0,
                    help="Remove ID3 v2.x tag.");
   grp1.add_option("--remove-all", action="store_true",
                    dest="remove_all", default=0,
                    help="Remove both ID3 v1.x and v2.x tags.");
   optParser.add_option_group(grp1);

   # Misc. options.
   grp3 = OptionGroup(optParser, "Misc. Options");
   grp3.add_option("--rename", type="string", action="store",
                   dest="rename_pattern", metavar="NAME",
                   help="Rename file (the extension is not affected) based on "\
                        "data in the tag using substitution variables: "\
                        "%A (artist), %a (album), %t (title), "\
                        "%n (track number), and %N (total number of tracks)");
   grp3.add_option("--fs-encoding", type="string", action="store",
                   dest="fs_encoding", default=sys.getfilesystemencoding(),
                   metavar="ENCODING",
                   help="Use the specified character encoding for the "\
                        "filename when renaming files");
   grp3.add_option("-l", "--list-genres", action="store_true",
                   dest="showGenres",
                   help="Display the table of ID3 genres and exit");
   grp3.add_option("--list-image-types", action="store_true",
                   dest="showImagesTypes",
                   help="List all possible image types");
   grp3.add_option("--strict", action="store_true",
                   dest="strict", help="Fail for tags that violate "\
                                       "the ID3 specification.");
   grp3.add_option("--jep-118", action="store_true", dest="jep_118",
                   help="Output the tag per the format described in JEP-0118. "\
                        "See http://www.xmpp.org/extensions/xep-0118.html");
   grp3.add_option("--nfo", action="store_true", dest="nfo",
                   help="Output NFO information.")
   grp3.add_option("--lametag", action="store_true", dest="lametag",
                   help="Prints the LAME Tag.")
   grp3.add_option("--force-update", action="store_true", dest="force_update",
                   default=0,
                   help="Update the tag regardless of whether any frames are "\
                        "set with new values.");
   grp3.add_option("--no-color", action="store_true",
                   dest="nocolor", help="Disable color output");
   grp3.add_option("--no-zero-padding", action="store_false",
                   dest="zeropad", default=True,
                   help="Don't pad track or disc numbers with 0's");
   grp3.add_option("--no-tagging-time-frame", action="store_true",
                    dest="no_tdtg", default=0,
                    help="When saving tags do not add a TDTG (tagging time) "
                         "frame")
   grp3.add_option("-F", dest="field_delim", default=':', metavar="DELIM",
                   help="Specify a new delimiter for option values that "
                        "contain multiple fields (default delimiter is ':')")
   grp3.add_option("-v", "--verbose", action="store_true",
                   dest="verbose", help="Show all available information");
   grp3.add_option("--debug", action="store_true", dest="debug",
                   help="Trace program execution.");
   grp3.add_option('--run-profiler', action='store_true',
                   dest='run_profiler', help='Run using python profiler.')
   optParser.add_option_group(grp3);

   return optParser;

################################################################################
def printGenres():
    genres = [];
    displayed = []
    # Filter out 'Unknown'
    for g in eyeD3.genres:
        if g != "Unknown":
            genres.append(g);

    cols = 2;
    offset = int(math.ceil(float(len(genres)) / cols));
    for i in range(offset):
       c1, c2 = '', ''
       if i < len(genres):
          if i not in displayed:
              c1 = "%3d: %s" % (i, genres[i]);
              displayed.append(i)
       else:
          c1 = "";
       if (i * 2) < len(genres):
           try:
              if (i + offset) not in displayed:
                  c2 = "%3d: %s" % (i + offset, genres[i + offset]);
                  displayed.append(i + offset)
           except IndexError:
               pass
       else:
          c2 = "";
       print c1 + (" " * (40 - len(c1))) + c2;
    print ""

################################################################################
def printImageTypes():
    print "Available image types for --add-image:";
    for type in range(eyeD3.frames.ImageFrame.MIN_TYPE,
                      eyeD3.frames.ImageFrame.MAX_TYPE + 1):
        print "\t%s" % (eyeD3.frames.ImageFrame.picTypeToString(type));

################################################################################
def boldText(s, c = None):
    if c:
        return colors["bold"] + c + s + colors["normal"];
    return colors["bold"] + s + colors["normal"];

def printMsg(s):
    sys.stdout.write(s + '\n');

def printWarning(s):
    sys.stderr.write(colors["warning"] + str(s) + colors["normal"] + '\n');

def printError(s):
    sys.stderr.write(colors["error"] + str(s) + colors["normal"] + '\n');

################################################################################
class TagDriverBase(eyeD3.utils.FileHandler):
   def __init__(self, opts):
       self.opts = opts;

   def handleFile(self, f):
      self.audioFile = None;
      self.tag = None;

      try:
         if eyeD3.tag.isMp3File(f):
            self.audioFile = eyeD3.tag.Mp3AudioFile(f, self.opts.tagVersion);
            self.tag = self.audioFile.getTag();
         else:
            self.tag = eyeD3.Tag();
            if not self.tag.link(f, self.opts.tagVersion):
               self.tag = None;
      except (eyeD3.tag.InvalidAudioFormatException,
              eyeD3.tag.TagException, IOError), ex:
         printError(ex);
         return self.R_CONT;

class NFODriver(TagDriverBase):
   def __init__(self, opts):
       TagDriverBase.__init__(self, opts)
       self.albums = {}

   def handleFile(self, f):
       TagDriverBase.handleFile(self, f)

       if self.audioFile and self.audioFile.getTag():
           tag = self.audioFile.getTag()
           album = self.tag.getAlbum()
           if album and not self.albums.has_key(album):
               self.albums[album] = []
               self.albums[album].append(self.audioFile)
           elif album:
               self.albums[album].append(self.audioFile)

   def handleDone(self):
       if not self.albums:
           return

       import time
       for album in self.albums:
           audio_files = self.albums[album]
           audio_files.sort(key=lambda af: af.getTag().getTrackNum())

           max_title_len = 0
           avg_bitrate = 0
           encoder_info = ''
           for audio_file in audio_files:
               tag = audio_file.getTag()
               # Compute maximum title length
               title_len = len(tag.getTitle())
               if title_len > max_title_len:
                   max_title_len = title_len
               # Compute average bitrate
               avg_bitrate += audio_file.getBitRate()[1]
               # Grab the last lame version in case not all files have one
               if audio_file.lameTag.has_key('encoder_version'):
                   encoder_info = (audio_file.lameTag['encoder_version']
                                   or encoder_info)
           avg_bitrate = avg_bitrate / len(audio_files)

           printMsg("Artist: %s" % audio_files[0].getTag().getArtist())
           printMsg("Album : %s" % album)
           printMsg("Year  : %s" % audio_files[0].getTag().getYear())
           genre = audio_files[0].getTag().getGenre()
           if genre:
               genre = genre.getName()
           else:
               genre = ""
           printMsg("Genre : %s" % genre)

           printMsg("")
           printMsg("Source: ")
           printMsg("Encoder: %s" % encoder_info)
           printMsg("Codec  : mp3")
           printMsg("Bitrate: ~%s K/s @ %s Hz, %s" %
                    (avg_bitrate, audio_files[0].header.sampleFreq,
                     audio_files[0].header.mode))
           printMsg("Tag    : ID3 %s" %
                    audio_files[0].getTag().getVersionStr())

           printMsg("")
           printMsg("Ripped By: ")

           printMsg("")
           printMsg("Track Listing")
           printMsg("-------------")
           count = 0
           total_time = 0
           total_size = 0
           for audio_file in audio_files:
               tag = audio_file.getTag()
               count += 1

               title = tag.getTitle()
               title_len = len(title)
               padding = " " * ((max_title_len - title_len) + 3)
               total_time += audio_file.getPlayTime()
               total_size += audio_file.getSize()

               zero_pad = "0" * (len(str(len(audio_files))) - len(str(count)))
               printMsg(" %s%d. %s%s(%s)" % (zero_pad, count, title, padding,
                                             audio_file.getPlayTimeString()))

           printMsg("")
           printMsg("Total play time: %s" %
                    eyeD3.utils.format_track_time(total_time))
           printMsg("Total size     : %s" % eyeD3.utils.format_size(total_size))

           printMsg("")
           printMsg("=" * 78)
           printMsg(".NFO file created with eyeD3 %s on %s" %
                    (eyeD3.eyeD3Version, time.asctime()))
           printMsg("For more information about eyeD3 go to %s" %
                    "http://eyeD3.nicfit.net/")
           printMsg("=" * 78)

class JEP118Driver(TagDriverBase):
   def __init__(self, opts):
       TagDriverBase.__init__(self, opts)

   def handleFile(self, f):
       TagDriverBase.handleFile(self, f)
       if self.tag:
           xml = eyeD3.tag.tagToUserTune(self.audioFile or self.tag);
           printMsg(xml.encode(ENCODING, "replace"));
           return self.R_CONT;

class EyeD3Driver(TagDriverBase):
   def __init__(self, opts):
       TagDriverBase.__init__(self, opts)

   def handleFile(self, f):
      self.printHeader(f);
      TagDriverBase.handleFile(self, f)

      self.printAudioInfo(self.audioFile);

      if not self.tag:
         printError("No ID3 %s tag found!" %\
                    eyeD3.utils.versionToString(self.opts.tagVersion));

      try:
         # Handle frame removals.
         if self.tag and self.handleRemoves(self.tag):
            self.tag = None;

         # Create a new tag in case values are being added, or the tag
         # was removed.
         newTag = 0;
         if not self.tag:
            self.tag = eyeD3.Tag(f);
            self.tag.header.setVersion(self.opts.tagVersion);
            newTag = 1;

         # Handle frame edits.
         try:
             tagModified = self.handleEdits(self.tag) or self.opts.force_update;
         except CommandException, ex:
             printError(ex);
             return self.R_HALT;

         if newTag and not tagModified and not self.opts.convertVersion:
            return self.R_CONT;

         # Handle updating the tag if requested.
         if tagModified or self.opts.convertVersion:
            updateVersion = eyeD3.ID3_CURRENT_VERSION;
            if self.opts.convertVersion:
               updateVersion = self.opts.convertVersion;
               v = eyeD3.utils.versionToString(updateVersion);
               if updateVersion == self.tag.getVersion():
                  printWarning("No conversion necessary, tag is "\
                               "already version %s" % v);
               else:
                  printWarning("Converting tag to ID3 version %s" % v);
            elif self.opts.tagVersion != eyeD3.ID3_ANY_VERSION:
               updateVersion = self.opts.tagVersion;

            # Update the tag.
            printWarning("Writing tag...");
            self.tag.do_tdtg = not self.opts.no_tdtg
            if not self.tag.update(updateVersion):
               printError("Error writing tag: %s" % f);
               return self.R_HALT;
         else:
            if newTag:
               # No edits were performed so we can ditch the _new_ tag.
               self.tag = None;
      except (eyeD3.tag.TagException, eyeD3.frames.FrameException), ex:
         printError(ex);
         return self.R_CONT;

      # Print tag.
      try:
          if self.tag:
             self.printTag(self.tag);
             if self.opts.verbose:
                printMsg("-" * 79);
                printMsg("ID3 Frames:");
                for frm in self.tag:
                   printMsg(unicode(frm).encode(ENCODING, "replace"))
      except (UnicodeEncodeError, UnicodeDecodeError, CommandException), ex:
         printError(ex);
         return self.R_CONT;

      # Handle file renaming.
      # FIXME: Should a audioFile be required here?
      if self.audioFile and self.tag and self.opts.rename_pattern:
          self.handleRenames(self.audioFile, self.opts.rename_pattern,
                             self.opts.fs_encoding);

      return self.R_CONT;

   def handleRemoves(self, tag):
      # Remove if requested.
      removeVersion = 0;
      status = 0;
      rmStr = "";
      if self.opts.remove_all:
         removeVersion = eyeD3.ID3_ANY_VERSION;
         rmStr = "v1.x and/or v2.x";
      elif self.opts.remove_v1:
         removeVersion = eyeD3.ID3_V1;
         rmStr = "v1.x";
      elif self.opts.remove_v2:
         removeVersion = eyeD3.ID3_V2;
         rmStr = "v2.x";

      if removeVersion:
         status = tag.remove(removeVersion);
         statusStr = self.boolToStatus(status);
         printWarning("Removing ID3 %s tag: %s" % (rmStr, statusStr));

      return status;

   def handleEdits(self, tag):
      retval = 0;

      artist = self.opts.artist;
      if artist != None:
         printWarning("Setting artist: %s" % artist);
         tag.setArtist(artist);
         retval |= 1;

      album = self.opts.album;
      if album != None:
         printWarning("Setting album: %s" % album);
         tag.setAlbum(album);
         retval |= 1;

      title = self.opts.title;
      if title != None:
         printWarning("Setting title: %s" % title);
         tag.setTitle(title);
         retval |= 1;

      trackNum = self.opts.track;
      trackTotal = self.opts.track_total;
      if trackNum != None or trackTotal != None:
         if trackNum:
            printWarning("Setting track: %s" % str(trackNum));
            trackNum = int(trackNum);
         else:
            trackNum = tag.getTrackNum()[0];
         if trackTotal:
            printWarning("Setting track total: %s" % str(trackTotal));
            trackTotal = int(trackTotal);
         else:
            trackTotal = tag.getTrackNum()[1];
         tag.setTrackNum((trackNum, trackTotal), zeropad = self.opts.zeropad);
         retval |= 1;

      genre = self.opts.genre;
      if genre != None:
         printWarning("Setting track genre: %s" % genre);
         tag.setGenre(genre);
         retval |= 1;

      year = self.opts.year;
      if year != None:
         printWarning("Setting year: %s" % year);
         tag.setDate(year);
         retval |= 1;

      play_count = self.opts.play_count;
      if play_count != None:
          incr = False;
          try:
              if play_count[0] == '+':
                  incr = True;
                  play_count = long(play_count[1:]);
              else:
                  play_count = long(play_count);
          except ValueError:
              raise CommandException("Invalid --play-count value: %s" %\
                                     play_count);

          if play_count < 0:
              raise CommandException("Play count argument %d < 0" %\
                                     (play_count));
          if incr:
              printWarning("Incrementing play count: +%d" % (play_count));
              tag.incrementPlayCount(play_count);
          else:
              printWarning("Setting play count: %d" % (play_count));
              tag.setPlayCount(play_count);
          retval |= 1;

      bpm = self.opts.bpm;
      if bpm != None:
          try:
              bpm_float = float(bpm)
              bpm = int(bpm_float + 0.5);
              if bpm <= 0:
                  raise ValueError();
              printWarning("Setting BPM: %d" % (bpm));
              tag.setBPM(bpm);
              retval |= 1;
          except ValueError:
              raise CommandException("Invalid --bpm value: %s" % bpm);

      pub = self.opts.publisher;
      if pub != None:
          printWarning("Setting publisher: %s" % (pub));
          tag.setPublisher(pub);
          retval |= 1;

      comments = self.opts.comments;
      if self.opts.remove_comments:
         count = tag.removeComments();
         printWarning("Removing %d comment frames" % count);
         retval |= 1;
      elif comments:
         for c in comments:
            try:
               (lang,desc,comm) = c.split(self.opts.field_delim, 2)
               if not lang:
                  lang = eyeD3.DEFAULT_LANG;
               if not comm:
                   printWarning("Removing comment: %s" % (desc));
               else:
                   printWarning("Setting comment: [%s]: %s" % (desc, comm));
               tag.addComment(comm, desc, lang);
               retval |= 1;
            except ValueError:
               printError("Invalid Comment; see --help: %s" % c);
               retval &= 0;

      lyrics = self.opts.lyrics;
      if self.opts.remove_lyrics:
         count = tag.removeLyrics();
         printWarning("Removing %d lyrics frames" % count);
         retval |= 1;
      elif lyrics:
         for l in lyrics:
            try:
               (lang,desc,lyrics) = l.split(self.opts.field_delim, 2)
               if not lang:
                  lang = eyeD3.DEFAULT_LANG;
               if not lyrics:
                   printWarning("Removing lyrics: %s" % (desc));
               else:
                   printWarning("Setting lyrics: [%s]: %s" % (desc, lyrics));
               tag.addLyrics(lyrics, desc, lang);
               retval |= 1;
            except ValueError:
               printError("Invalid Lyrics; see --help: %s" % l);
               retval &= 0;

      if self.opts.remove_images:
          count = tag.removeImages()
          printWarning("Removing %d image frames" % count);
          retval |= 1;
      elif self.opts.images:
          for i in self.opts.images:
              img_args = i.split(self.opts.field_delim)
              if len(img_args) < 2:
                  raise TagException("Invalid --add-image argument: %s" % i);
              else:
                 ptype = eyeD3.frames.ImageFrame.stringToPicType(img_args[1]);
                 path = img_args[0];
                 if not path:
                     printWarning("Removing image %s" % path);
                     tag.addImage(ptype, None, None);
                 else:
                     printWarning("Adding image %s" % path);
                     desc = u"";
                     if (len(img_args) > 2) and img_args[2]:
                         desc = unicode(img_args[2]);
                     tag.addImage(ptype, path, desc);
                 retval |= 1;

      # GEOB frames
      if self.opts.objects:
          for i in self.opts.objects:
              obj_args = i.split(self.opts.field_delim)
              if len(obj_args) < 1:
                  raise TagException("Invalid --add-object argument: %s" % i);
              else:
                 path = obj_args[0];
                 desc = u"";
                 if (len(obj_args) > 1) and obj_args[1]:
                     desc = unicode(obj_args[1]);
                 if not path:
                     printWarning("Removing object %s" % desc);
                     tag.addObject(None, None, desc, None);
                 else:
                     mime = "";
                     filename = None;
                     if (len(obj_args) > 2) and obj_args[2]:
                         mime = obj_args[2];
                     if (len(obj_args) > 3):
                         filename = unicode(obj_args[3]);
                     printWarning("Adding object %s" % path);
                     tag.addObject(path, mime, desc, filename);
                 retval |= 1;

      if self.opts.textFrames or self.opts.userTextFrames:
          for tf in self.opts.textFrames:
              tf_args = tf.split(self.opts.field_delim, 1)
              if len(tf_args) < 2:
                  raise TagException("Invalid --set-text-frame argument: "\
                                     "%s" % tf)
              else:
                  if tf_args[1]:
                      printWarning("Setting %s frame to '%s'" % (tf_args[0],
                                                                 tf_args[1]));
                  else:
                      printWarning("Removing %s frame" % (tf_args[0]));
                  try:
                      tag.setTextFrame(tf_args[0], tf_args[1]);
                      retval |= 1;
                  except FrameException, ex:
                      printError(ex);
                      retval &= 0;
          for tf in self.opts.userTextFrames:
              tf_args = tf.split(self.opts.field_delim, 1)
              if len(tf_args) < 2:
                  raise TagException("Invalid --set-user-text-frame argument: "\
                                     "%s" % tf)
              else:
                  if tf_args[1]:
                      printWarning("Setting '%s' TXXX frame to '%s'" %\
                                   (tf_args[0], tf_args[1]));
                  else:
                      printWarning("Removing '%s' TXXX frame" % (tf_args[0]));
                  try:
                      tag.addUserTextFrame(tf_args[0], tf_args[1]);
                      retval |= 1;
                  except FrameException, ex:
                      printError(ex);
                      retval &= 0;

      if self.opts.url_frames or self.opts.user_url_frames:
          # Make a list of tuples (is_user_frame, arg)
          frames = [(f in self.opts.user_url_frames, f)
                    for f in (self.opts.url_frames + self.opts.user_url_frames)]

          for user_frame, f in frames:
              args = f.split(self.opts.field_delim, 1)
              if len(args) < 2:
                  raise TagException("Invalid argument: %s" % f)

              desc, fid, url = None, None, None
              if user_frame:
                  # FIXME
                  fid = "WXXX"
                  desc, url = args
              else:
                  fid, url = args

              if url:
                  printWarning("Setting %s frame to '%s'" % (fid, url))
              else:
                  printWarning("Removing %s frame" % fid)
              try:
                  if not user_frame:
                      tag.setURLFrame(fid, url)
                  else:
                      tag.addUserURLFrame(desc, url)
                  retval |= 1
              except FrameException, ex:
                  printError(ex)
                  retval &= 0

      if self.opts.textEncoding:
          e = self.opts.textEncoding;
          if e == "latin1":
              enc = LATIN1_ENCODING;
          elif e == "utf8":
              enc = UTF_8_ENCODING;
          elif e == "utf16-BE":
              enc = UTF_16BE_ENCODING;
          elif e == "utf16-LE":
              enc = UTF_16_ENCODING;
          else:
              raise TagException("Invalid encoding: %s" % (e));
          tag.setTextEncoding(enc);

      unique_file_ids = self.opts.unique_file_ids;
      if unique_file_ids:
         for ufid in unique_file_ids:
            try:
               sep = ufid.rfind(self.opts.field_delim)
               if sep < 0:
                   raise ValueError()
               owner_id = ufid[:sep]
               id = ufid[sep + 1:]

               if not owner_id:
                   raise ValueError();
               if not id:
                   printWarning("Removing unique file ID: %s" % owner_id);
               else:
                   printWarning("Setting unique file ID: [%s]: %s" %\
                                (owner_id, id));
               tag.addUniqueFileID(owner_id, id);
               retval |= 1;
            except ValueError:
               printError("Invalid unique file id argument; see --help: %s" %\
                          ufid);
               retval &= 0;

      return retval;

   def handleRenames(self, f, pattern, fs_encoding):
       try:
           name = f.getTag().tagToString(pattern);
           printWarning("Renaming file to '%s'" % (name.encode(fs_encoding,
                                                               'replace')));
           f.rename(name, fs_encoding);
       except TagException, ex:
           printError(ex);

   def boolToStatus(self, b):
      if b:
         return "SUCCESS";
      else:
         return "FAIL";

   def printHeader(self, filePath):
      fileSize = os.stat(filePath)[ST_SIZE]
      size_str = eyeD3.utils.format_size(fileSize)
      print "";
      print "%s\t%s[ %s ]%s" % (boldText(os.path.basename(filePath),
                                         colors["header"]),
                                colors["header"], size_str, colors["normal"]);
      print ("-" * 79);

   def printAudioInfo(self, audioInfo):
      if isinstance(audioInfo, eyeD3.Mp3AudioFile):
         print boldText("Time: ") +\
               "%s\tMPEG%d, Layer %s\t[ %s @ %s Hz - %s ]" %\
               (audioInfo.getPlayTimeString(), audioInfo.header.version,
                "I" * audioInfo.header.layer, audioInfo.getBitRateString(),
                audioInfo.header.sampleFreq, audioInfo.header.mode);
         print ("-" * 79);
      else:
         # Handle what it is known and silently ignore anything else.
         pass;

   def printTag(self, tag):
      if isinstance(tag, eyeD3.Tag):
         printMsg("ID3 %s:" % tag.getVersionStr());
         printMsg("%s: %s\t\t%s: %s" % (boldText("title"),
                                        tag.getTitle().encode(ENCODING,
                                                              "replace"),
                                        boldText("artist"),
                                        tag.getArtist().encode(ENCODING,
                                                               "replace")));
         printMsg("%s: %s\t\t%s: %s" % (boldText("album"),
                                        tag.getAlbum().encode(ENCODING,
                                                              "replace"),
                                        boldText("year"), tag.getYear()));

         trackStr = "";
         (trackNum, trackTotal) = tag.getTrackNum();
         if trackNum != None:
            trackStr = str(trackNum);
            if trackTotal:
               trackStr += "/%d" % trackTotal;
         genre = None;
         try:
            genre = tag.getGenre();
         except eyeD3.GenreException, ex:
            printError(ex);
         genreStr = "";
         if genre:
            genreStr = "%s: %s (id %s)" % (boldText("genre"), genre.getName(),
                                           str(genre.getId()));
         printMsg("%s: %s\t\t%s" % (boldText("track"), trackStr, genreStr));

         # PCNT
         play_count = tag.getPlayCount();
         if play_count != None:
             printMsg("%s %d" % (boldText("Play Count:"), play_count));

         # TBPM
         bpm = tag.getBPM();
         if bpm != None:
             printMsg("%s %d" % (boldText("BPM:"), bpm));

         # TPUB
         pub = tag.getPublisher();
         if pub != None:
             printMsg("%s %s" % (boldText("Publisher/label:"), pub));

         # UFID
         unique_file_ids = tag.getUniqueFileIDs();
         if unique_file_ids:
             for ufid in unique_file_ids:
                 printMsg("%s [%s] %s" % (boldText("Unique File ID:"),
                                          ufid.owner_id, ufid.id));

         # COMM
         comments = tag.getComments();
         for c in comments:
            cLang = c.lang;
            if cLang == None:
               cLang = "";
            cDesc = c.description;
            if cDesc == None:
               cDesc = "";
            cText = c.comment;
            printMsg("%s: [Description: %s] [Lang: %s]\n%s" %\
                     (boldText("Comment"), cDesc, cLang,
                      cText.encode(ENCODING,"replace")));

         # USLT
         lyrics = tag.getLyrics();
         for l in lyrics:
            lLang = l.lang;
            if lLang == None:
               lLang = "";
            lDesc = l.description;
            if lDesc == None:
               lDesc = "";
            lText = l.lyrics.replace('\r', '\n');
            printMsg("%s: [Description: %s] [Lang: %s]\n%s" %\
                     (boldText("Lyrics"), lDesc, lLang,
                      lText.encode(ENCODING,"replace")));

         userTextFrames = tag.getUserTextFrames();
         if userTextFrames:
            print "";
         for f in userTextFrames:
            desc = f.description;
            if not desc:
               desc = "";
            text = f.text;
            print "%s: [Description: %s]\n%s" % \
                  (boldText("UserTextFrame"), desc,
                   text.encode(ENCODING,"replace"));

         urls = tag.getURLs();
         if urls:
            print "";
         for u in urls:
            if u.header.id != eyeD3.frames.USERURL_FID:
               print "%s: %s" % (u.header.id, u.url);
            else:
               print "%s [Description: %s]: %s" % (u.header.id, u.description,
                                                   u.url)

         images = tag.getImages();
         if images:
            print "";
         for img in images:
            print "%s: [Size: %d bytes] [Type: %s]" % \
                  (boldText(img.picTypeToString(img.pictureType) + " Image"),
                   len(img.imageData), img.mimeType);
            print "Description: %s" % img.description;
            print "\n";
            if self.opts.writeImages:
               img_path = self.opts.writeImages + os.sep;
               if not os.path.exists(img_path):
                   raise CommandException("Directory does not exist: %s" %\
                                          img_path);
               img_file = img.getDefaultFileName();
               count = 1;
               while os.path.exists(img_path + img_file):
                   img_file = img.getDefaultFileName(str(count));
                   count += 1;
               printWarning("Writing %s..." % (img_path + img_file));
               img.writeFile(img_path, img_file);

         objects = tag.getObjects();
         if objects:
            print "";
         for obj in objects:
            print "%s: [Size: %d bytes] [Type: %s]" % \
                  (boldText("GEOB"),
                  len(obj.objectData), obj.mimeType);
            print "Description: %s" % obj.description;
            print "Filename: %s" % obj.filename;
            print "\n";
            if self.opts.writeObjects:
               obj_path = self.opts.writeObjects + os.sep;
               if not os.path.exists(obj_path):
                   raise CommandException("Directory does not exist: %s" %\
                                          obj_path);
               obj_file = obj.getDefaultFileName();
               count = 1;
               while os.path.exists(obj_path + obj_file):
                   obj_file = obj.getDefaultFileName(str(count));
                   count += 1;
               printWarning("Writing %s..." % (obj_path + obj_file));
               obj.writeFile(obj_path, obj_file);

      else:
         raise TypeError("Unknown tag type: " + str(type(tag)));

class LameTagDriver(EyeD3Driver):
   def __init__(self, opts):
      EyeD3Driver.__init__(self, opts)

   def handleFile(self, f):
      TagDriverBase.handleFile(self, f)

      self.printHeader(f);
      if not self.audioFile or not self.audioFile.lameTag:
         printMsg('No LAME Tag')
         return self.R_CONT

      format = '%-20s: %s'
      lt = self.audioFile.lameTag
      if not lt.has_key('infotag_crc'):
         try:
            printMsg('%s: %s' % ('Encoder Version', lt['encoder_version']))
         except KeyError:
            pass
         return self.R_CONT

      values = []

      values.append(('Encoder Version', lt['encoder_version']))
      values.append(('LAME Tag Revision', lt['tag_revision']))
      values.append(('VBR Method', lt['vbr_method']))
      values.append(('Lowpass Filter', lt['lowpass_filter']))
      if lt.has_key('replaygain'):
         try:
            peak = lt['replaygain']['peak_amplitude']
            db = 20 * math.log10(peak)
            val = '%.8f (%+.1f dB)' % (peak, db)
            values.append(('Peak Amplitude', val))
         except KeyError: pass
         for type in ['radio', 'audiofile']:
            try:
               gain = lt['replaygain'][type]
               name = '%s Replay Gain' % gain['name'].capitalize()
               val = '%s dB (%s)' % (gain['adjustment'], gain['originator'])
               values.append((name, val))
            except KeyError: pass
      values.append(('Encoding Flags', ' '.join((lt['encoding_flags']))))
      if lt['nogap']:
         values.append(('No Gap', ' and '.join(lt['nogap'])))
      values.append(('ATH Type', lt['ath_type']))
      values.append(('Bitrate (%s)' % lt['bitrate'][1], lt['bitrate'][0]))
      values.append(('Encoder Delay', '%s samples' % lt['encoder_delay']))
      values.append(('Encoder Padding', '%s samples' % lt['encoder_padding']))
      values.append(('Noise Shaping', lt['noise_shaping']))
      values.append(('Stereo Mode', lt['stereo_mode']))
      values.append(('Unwise Settings', lt['unwise_settings']))
      values.append(('Sample Frequency', lt['sample_freq']))
      values.append(('MP3 Gain', '%s (%+.1f dB)' % (lt['mp3_gain'],
                                                    lt['mp3_gain'] * 1.5)))
      values.append(('Preset', lt['preset']))
      values.append(('Surround Info', lt['surround_info']))
      values.append(('Music Length', '%s' % format_size(lt['music_length'])))
      values.append(('Music CRC-16', '%04X' % lt['music_crc']))
      values.append(('LAME Tag CRC-16', '%04X' % lt['infotag_crc']))

      for v in values:
         printMsg(format % (v))

################################################################################
def main():
   progname = os.path.basename(sys.argv[0])

   # Process command line.
   optParser = getOptionParser();
   (options, args) = optParser.parse_args();

   # Handle -l, --list-genres
   if options.showGenres:
      printGenres();
      return 0;
   # Handle --list-image-types
   if options.showImagesTypes:
      printImageTypes();
      return 0;

   if len(args) == 0:
      optParser.error("File/directory argument(s) required");
      return 1;

   if options.jep_118:
       # Handle --jep-118
       app = JEP118Driver(options);
   elif options.nfo:
       # Handle --nfo
       app = NFODriver(options);
   elif options.lametag:
       # Handle --lametag
       app = LameTagDriver(options)
   else:
       # Main driver
       if options.debug:
           # Handle --debug
           eyeD3.utils.TRACE = 1;
       if options.strict:
           # Handle --strict
           eyeD3.utils.STRICT_ID3 = 1;
       if options.nocolor:
           # Handle --nocolor
           colors.enabled(0);
       app = EyeD3Driver(options);

   # Process files/directories
   for f in args:
      if os.path.isfile(f):
         retval = app.handleFile(f);
      elif os.path.isdir(f):
         fwalker = FileWalker(app, f);
         retval = fwalker.go();
      else:
         printError("File Not Found: %s" % f);
         retval = 1;

   return retval;

#######################################################################
if __name__ == "__main__":
    retval = 0
    profiling = False
    profile_out = None

    try:
        if "--run-profiler" in sys.argv:
            profiling = True
            profile_out = 'eyeD3-profiler.out'
            import profile
            profile.run('main()', profile_out)
        else:
            retval = main();
    except KeyboardInterrupt:
        retval = 0
    except Exception, ex:
        import traceback
        print >>sys.stderr, "Uncaught exception:", str(ex)
        print >>sys.stderr, traceback.format_exc()
        retval = 1
    finally:
        if profiling:
            import pstats
            p = pstats.Stats(profile_out)
            p.sort_stats('cumulative').print_stats(100)

    sys.exit(retval)