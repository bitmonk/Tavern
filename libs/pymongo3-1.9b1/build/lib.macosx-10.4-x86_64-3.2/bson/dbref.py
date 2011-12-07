# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for manipulating DBRefs (references to MongoDB documents)."""

from bson.son import SON
from copy import deepcopy


class DBRef(object):
    """A reference to a document stored in MongoDB.
    """

    def __init__(self, collection, id, database=None, _extra={}, **kwargs):
        """Initialize a new :class:`DBRef`.

        Raises :class:`TypeError` if `collection` or `database` is not
        an instance of :class:`str`. `database` is optional and
        allows references to documents to work across databases. Any
        additional keyword arguments will create additional fields in
        the resultant embedded document.

        :Parameters:
          - `collection`: name of the collection the document is stored in
          - `id`: the value of the document's ``"_id"`` field
          - `database` (optional): name of the database to reference
          - `**kwargs` (optional): additional keyword arguments will
            create additional, custom fields

        .. versionchanged:: 1.8
           Now takes keyword arguments to specify additional fields.
        .. versionadded:: 1.1.1
           The `database` parameter.

        .. mongodoc:: dbrefs
        """
        if not isinstance(collection, str):
            raise TypeError("collection must be an instance of str")
        if database is not None and not isinstance(database, str):
            raise TypeError("database must be an instance of str")

        self.__collection = collection
        self.__id = id
        self.__database = database
        kwargs.update(_extra)
        self.__kwargs = kwargs

    @property
    def collection(self):
        """Get the name of this DBRef's collection as unicode.
        """
        return self.__collection

    @property
    def id(self):
        """Get this DBRef's _id.
        """
        return self.__id

    @property
    def database(self):
        """Get the name of this DBRef's database.

        Returns None if this DBRef doesn't specify a database.

        .. versionadded:: 1.1.1
        """
        return self.__database

    def __getattr__(self, key):
        return self.__kwargs[key]

    def as_doc(self):
        """Get the SON document representation of this DBRef.

        Generally not needed by application developers
        """
        doc = SON([("$ref", self.collection),
                   ("$id", self.id)])
        if self.database is not None:
            doc["$db"] = self.database
        doc.update(self.__kwargs)
        return doc

    def __repr__(self):
        extra = "".join([", %s=%r" % (k, v)
                         for k, v in self.__kwargs.items()])
        if self.database is None:
            return "DBRef(%r, %r%s)" % (self.collection, self.id, extra)
        return "DBRef(%r, %r, %r%s)" % (self.collection, self.id,
                                        self.database, extra)

    def __eq__(self, other):
        if isinstance(other, DBRef):
            mylist = [self.__database, self.__collection,
                      self.__id, self.__kwargs]
            otherlist = [other.__database, other.__collection,
                         other.__id, other.__kwargs]
            return mylist == otherlist
        return NotImplemented

    def __hash__(self):
        """Get a hash value for this :class:`DBRef`.

        .. versionadded:: 1.1
        """
        return hash((self.__collection, self.__id,
                     self.__database, self.__kwargs))

    def __deepcopy__(self, memo):
        """Support function for `copy.deepcopy()`.

        .. versionadded:: 1.10
        """
        return DBRef(deepcopy(self.__collection, memo),
                     deepcopy(self.__id, memo),
                     deepcopy(self.__database, memo),
                     deepcopy(self.__kwargs, memo))