#!/bin/bash


make_alot_theme()
{
cat <<EOF

#http://alot.readthedocs.org/en/latest/configuration/theming.html


###############################################################################
# SOLARIZED DARK
#
# colour theme for alot. © 2012 Patrick Totzke, GNU GPL3+
# http://ethanschoonover.com/solarized
# https://github.com/pazz/alot
###############################################################################
#
# Define mappings from solarized colour names to urwid attribute names for 16
# and 256 colour modes. These work well assuming you use the solarized term
# colours via Xressources/Xdefaults
# For urxvt, set 'URxvt.intensityStyles: false' in your ~/.Xdresources

base03 = 'dark gray'
base02 = 'black'
base01 = 'light green'
base00 = 'yellow'
base0 = 'default'
base1 = 'dark gray'
base2 = 'light gray'
base3 = 'white'
yellow = 'brown'
orange = 'light red'
red = 'dark red'
magenta = 'dark magenta'
violet = 'light magenta'
blue = 'dark blue'
cyan = 'dark cyan'
green = 'dark green'


[global]
    footer = 'standout','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    body = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base02)s'
    notify_error = 'standout','default','%(base3)s','%(red)s','%(base3)s','%(red)s'
    notify_normal = 'default','default','%(blue)s','%(base02)s','%(blue)s','%(base02)s'
    prompt = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    tag = 'default','default','%(yellow)s','%(base03)s','%(yellow)s','%(base02)s'
    tag_focus = 'standout','default','%(base03)s','%(yellow)s','%(base03)s','%(yellow)s'
[help]
    text = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    section = 'underline','default','%(cyan)s,bold','%(base02)s','%(cyan)s,bold','%(base02)s'
    title = 'standout','default','%(yellow)s','%(base02)s','%(yellow)s','%(base02)s'
    frame = 'standout','default','%(base1)s','%(base02)s','%(base1)s,bold','%(base02)s'
[namedqueries]
    line_even = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    line_focus = 'standout','default','%(base1)s','%(base01)s','%(base1)s','%(base01)s'
    line_odd = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
[taglist]
    line_even = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    line_focus = 'standout','default','%(base1)s','%(base01)s','%(base1)s','%(base01)s'
    line_odd = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
[bufferlist]
    line_even = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    line_focus = 'standout','default','%(base1)s','%(base01)s','%(base1)s','%(base01)s'
    line_odd = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
[thread]
    attachment = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base02)s'
    attachment_focus = 'underline','default','%(base02)s','%(yellow)s','%(base02)s','%(yellow)s'
    arrow_bars = 'default','default','%(yellow)s','%(base03)s','%(yellow)s','%(base03)s'
    arrow_heads = 'default','default','%(yellow)s','%(base03)s','%(yellow)s','%(base03)s'
    body = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base02)s'
    body_focus = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
    header = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
    header_key = 'default','default','%(red)s','%(base03)s','%(red)s','%(base03)s'
    header_value = 'default','default','%(blue)s','%(base03)s','%(blue)s','%(base03)s'
    [[summary]]
      even = 'default','default','%(base0)s','%(base02)s','%(base0)s','%(base02)s'
      focus = 'standout','default','%(base1)s','%(base01)s','%(base1)s','%(base01)s'
      odd = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
[envelope]
    body = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
    header = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
    header_key = 'default','default','%(red)s','%(base03)s','%(red)s','%(base03)s'
    header_value = 'default','default','%(blue)s','%(base03)s','%(blue)s','%(base03)s'
[search]
    [[threadline]]
        normal = 'default','default','%(base1)s','%(base03)s','%(base1)s','%(base02)s'
        focus = 'standout','default','%(base02)s','%(base01)s','%(base02)s','%(base01)s'
        parts = date,mailcount,tags,authors,subject
        [[[date]]]
            normal = 'default','default','%(yellow)s','%(base03)s','%(yellow)s','%(base02)s'
            focus = 'standout','default','%(base02)s,bold','%(base01)s','%(base02)s,bold','%(base01)s'
            alignment = right
            width = fit, 9, 9
        [[[mailcount]]]
            normal = 'default','default','%(blue)s','%(base03)s','%(blue)s','%(base03)s'
            focus = 'standout','default','%(base02)s','%(base01)s','%(base02)s','%(base01)s'
        [[[tags]]]
            normal = 'default','default','%(cyan)s','%(base03)s','%(cyan)s','%(base03)s'
            focus = 'standout','default','%(base02)s','%(base01)s','%(base02)s','%(base01)s'
        [[[authors]]]
            normal = 'default,underline','default','%(blue)s','%(base03)s','%(blue)s','%(base03)s'
            focus = 'standout','default','%(base02)s','%(base01)s','%(base02)s','%(base01)s'
            width = 'fit',0,30
        [[[subject]]]
            normal = 'default','default','%(base0)s','%(base03)s','%(base0)s','%(base03)s'
            focus = 'standout','default','%(base02)s,bold','%(base01)s','%(base02)s,bold','%(base01)s'
            width = 'weight',1
        [[[content]]]
            normal = 'default','default','%(base01)s','%(base03)s','%(base01)s','%(base03)s'
            focus = 'standout','default','%(base02)s','%(base01)s','%(base02)s','%(base01)s'
    [[threadline-unread]]
        normal = 'default','default','%(base1)s,bold','%(base03)s','%(base1)s,bold','%(base02)s'
        tagged_with = 'unread'
        [[[date]]]
            normal = 'default','default','%(yellow)s,bold','%(base03)s','%(yellow)s,bold','%(base03)s'
        [[[mailcount]]]
            normal = 'default','default','%(blue)s,bold','%(base03)s','%(blue)s,bold','%(base03)s'
        [[[tags]]]
            normal = 'bold','default','light cyan','%(base03)s','light cyan','%(base03)s'
        [[[authors]]]
            normal = 'default,underline','default','%(blue)s','%(base03)s','%(blue)s,bold','%(base03)s'
        [[[subject]]]
            normal = 'default','default','%(base2)s','%(base03)s','%(base2)s','%(base03)s'
        [[[content]]]
            normal = 'default','default','%(base01)s,bold','%(base03)s','%(base01)s,bold','%(base03)s'


EOF
}


make_alot_theme_old()
{
cat <<EOF

#http://alot.readthedocs.org/en/latest/configuration/theming.html

[global]
    footer = 'standout','','white,bold','dark blue','white,bold','#006'
    body = 'default','','dark gray','default','g58','default'
    notify_error = 'standout','','white','dark red','white','dark red'
    notify_normal = 'default','','light gray','dark gray','light gray','#68a'
    prompt = 'default','','light gray','black','light gray','g11'
    tag = 'default','','light gray','black','light gray','default'
    tag_focus = 'standout, bold','','white','dark gray','#ffa','#68a'
[help]
    text = 'default','','default','dark gray','default','g35'
    section = 'underline','','bold,underline','dark gray','bold,underline','g35'
    title = 'standout','','white','dark blue','white,bold,underline','g35'
[bufferlist]
    line_focus = 'standout','','yellow','light gray','#ff8','g58'
    line_even = 'default','','light gray','black','default','g3'
    line_odd = 'default','','light gray','black','default','default'
[taglist]
    line_focus = 'standout','','yellow','light gray','#ff8','g58'
    line_even = 'default','','light gray','black','default','g3'
    line_odd = 'default','','light gray','black','default','default'
[thread]
    arrow_heads = '','','dark red','','#a00',''
    arrow_bars = '','','dark red','','#800',''
    attachment = 'default','','light gray','dark gray','light gray','dark gray'
    attachment_focus = 'underline','','light gray','light green','light gray','light green'
    body = 'default','','light gray','default','light gray','default'
    body_focus = 'default','','light gray','default','white','default'
    header = 'default','','white','dark gray','white','dark gray'
    header_key = 'default','','white','dark gray','white','dark gray'
    header_value = 'default','','light gray','dark gray','light gray','dark gray'

    [[summary]]
        even = 'default','','white','light blue','white','#006'
        odd = 'default','','white','dark blue','white','#068'
        focus = 'standout','','white','light gray','#ff8','g58'

[envelope]
    body = 'default','','light gray','default','light gray','default'
    header = 'default','','white','dark gray','white','dark gray'
    header_key = 'default','','white','dark gray','white','dark gray'
    header_value = 'default','','light gray','dark gray','light gray','dark gray'
[search]
    [[threadline]]
        normal = 'default','','default','default','#6d6','default'
        focus = 'standout','','light gray','light gray','g85','g58'
        parts = date,mailcount,authors,subject,tags
        [[[date]]]
            normal = 'default','','light gray','default','g74','default'
            focus = 'standout','','yellow','light gray','yellow','g58'
            width = 'fit',10,10
            alignment = right
        [[[mailcount]]]
            normal = 'default','','light gray','default','g66','default'
            focus = 'standout','','yellow','light gray','yellow','g58'
            width = 'fit', 5,5
        [[[tags]]]
            normal = 'bold','','dark cyan','','dark cyan',''
            focus = 'standout','','yellow','light gray','yellow','g58'
        [[[authors]]]
            normal = 'default,underline','','light blue','default','#068','default'
            focus = 'standout','','yellow','light gray','yellow','g58'
            width = 'fit',0,30
        [[[subject]]]
            normal = 'default','','light gray','default','g66','default'
            focus = 'standout','','yellow','light gray','yellow','g58'
            width = 'weight', 1
        [[[content]]]
            normal = 'default','','light gray','default','dark gray','default'
            focus = 'standout','','yellow','light gray','yellow','g58'
            width = 'weight', 1

    # highlight threads containing unread messages
    [[threadline-unread]]
        tagged_with = 'unread'
        normal = 'default','','default,bold','default','#6d6,bold','default'
#        normal = 'default','default','light red,bold','default','light red,bold','default'
        parts = date,mailcount,authors,subject,tags
        [[[date]]]
            normal = 'default','','light gray,bold','default','white','default'
        [[[mailcount]]]
            normal = 'default','','light gray,bold','default','g93','default'
        [[[tags]]]
            normal = 'bold','','dark cyan,bold','','#6dd',''
        [[[authors]]]
            normal = 'default,underline','','light blue,bold','default','#68f','default'
        [[[subject]]]
            normal = 'default','','light gray,bold','default','g93','default'
        [[[content]]]
            normal = 'default','','light gray,bold','default','dark gray,bold','default'


EOF
}


make_alot_theme
