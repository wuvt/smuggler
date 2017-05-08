smuggler
========

smuggler is the Smart Music Upload Gadget for Gathered and Looted Electronic
Recordings. This is a user-facing web service that allows music to be imported
into impala's catalog and [moss](https://github.com/wuvt/moss)'s file store.


Usage
=====

``
pip3 install -r requirements.txt
export FLASK_DEBUG=1
export FLASK_APP=smuggler
flask run
``

The client.py script is included for example machine-to-machine usage.
