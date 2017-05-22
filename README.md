smuggler
========

smuggler is the Smart Music Upload Gadget for Gathered and Looted Electronic
Recordings. This is a user-facing web service that allows music to be imported
into impala's catalog and [moss](https://github.com/wuvt/moss)'s file store.


Usage
=====

```
pip3 install -r requirements.txt
export FLASK_DEBUG=1
export FLASK_APP=smuggler
flask run
```

The client.py script is included for example machine-to-machine usage.


License
=======

Copyright (c) 2017 Matt Hazinski

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see http://www.gnu.org/licenses/.
