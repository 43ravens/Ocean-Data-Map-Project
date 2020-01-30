#!/usr/bin/env python

import numpy as np
import xarray as xr

import data.calculated_parser.parser
from data.netcdf_data import NetCDFData
from data.sqlite_database import SQLiteDatabase
from data.variable import Variable
from data.variable_list import VariableList


class CalculatedData(NetCDFData):
    """Class for data that _may_ contain some variables that are calculated.
    Any variables that do not need calculation are passed along to the
    underlying dataset unchanged.
    """

    def __init__(self, url: str, **kwargs):
        """
        Parameters:
        url -- the URL for the dataset

        Keyword Parameters:
        calculated -- a dict of the calculated variables.
        """
        super(CalculatedData, self).__init__(url, **kwargs)
        if 'calculated' in kwargs:
            self._calculated = kwargs['calculated']
        else:
            self._calculated = {}

        self._calculated_variable_list = None

    def __get_calculated_dims(self, variable_key: str) -> list:
        try:
            return self._calculated[variable_key]['dims']
        except KeyError:
            raise KeyError(
                "{} does not have a dims attribute defined in datasetconfig.json. This is required for all calculated variables.".format(variable_key))

    def get_dataset_variable(self, key: str):
        """
        Returns the value of a given variable name from the dataset

        Parameters:
        key: The raw name of the variable (e.g. votemper, sspeed, etc.)
        """
        if key in self._calculated:
            # if the variable is a calculated one, return the CalculatedArray,
            # otherwise pass the request along to the underlying dataset.
            attrs = {}
            if key in super(CalculatedData, self).variables:
                attrs = super(CalculatedData,
                              self).get_dataset_variable(key).attrs

            attrs = {**attrs, **self._calculated[key]}

            return CalculatedArray(self._dataset,
                                   self._calculated[key]['equation'],
                                   self.__get_calculated_dims(key),
                                   attrs,
                                   self.url)
        else:
            return self._dataset.variables[key]

    @property
    def variables(self):
        """
        Returns a list of all data variables and their
        attributes in the dataset.
        """
        if self._calculated_variable_list is None:
            variable_list = super(CalculatedData, self).variables
            temp_list = list(variable_list)

            for name, data in self._calculated.items():
                if name not in variable_list:
                    # New Variable
                    temp_list.append(
                        Variable(
                            name,
                            data.get('long_name', name),
                            data.get('units', '1'),
                            self.__get_calculated_dims(name),
                            data.get('valid_min',
                                     np.finfo(np.float64).min),
                            data.get('valid_max',
                                     np.finfo(np.float64).max),
                        )
                    )
                else:
                    pass

            self._calculated_variable_list = VariableList(temp_list)

        return self._calculated_variable_list


class CalculatedArray():
    """This class is the equivalent of an xarray or netcdf Variable object, but
    parses the expression and does any requested calculations before returning
    data to the calling method.
    """

    def __init__(self, parent, expression, dims, attrs={}, db_url=""):
        """
        Parameters:
        parent -- the underlying dataset
        expression -- the equation to parse
        attrs -- optional, any attributes that the CalculatedArray should have
        """
        self._parent = parent
        self._expression: str = expression
        self._parser = data.calculated_parser.parser.Parser()
        self._parser.lexer.lexer.input(expression)
        self._dims: list = dims
        self._attrs: dict = attrs
        self._db_url: str = db_url
        self._shape: tuple = self.__calculate_var_shape()

        # This is a bit odd, but necessary. We run the expression through the
        # lexer so that the lexer variables get populated. This way we know the
        # list of underlying variables that are involved in the calculation
        # before we attempt to do any calculations. This is used to provide
        # information about the variable like shape, dimensions, etc.
        for _ in self._parser.lexer.lexer:
            pass

    def __getitem__(self, key):
        """This is where the magic happens.
        The dimensions of the key are determined by looking at the dimensions
        of all the underlying variables used in the calculation, this is then
        passed along to the parser where the calculation is performed.
        """
        key_dims = ()
        for v in self._parser.lexer.variables:
            if v not in self._parent.variables:
                continue

            d = self.__get_parent_variable_dims(v)

            if len(d) > len(key_dims):
                key_dims = d
            elif len(d) == len(key_dims):
                if d != key_dims:
                    return np.nan

        data = self._parser.parse(
            self._expression, self._parent, key, key_dims)

        return xr.DataArray(data)

    def __calculate_var_shape(self) -> tuple:
        # Determine shape of calculated variable based on its
        # declared dims in datasetconfig.json
        return tuple(self._parent[s].shape[0]
                     for s in self._dims)

    @property
    def attrs(self):
        class AttrDict(dict):
            def __init__(self, *args, **kwargs):
                super(AttrDict, self).__init__(*args, **kwargs)
                self.__dict__ = self

        return AttrDict(self._attrs)

    @property
    def shape(self) -> tuple:
        return self._shape

    @property
    def dims(self) -> list:
        return self._dims

    def __get_parent_variable_dims(self, variable: str):

        if hasattr(self._parent.variables[variable], "dims"):
            # xarray calls it dims
            return self._parent.variables[variable].dims
        else:
            return self._parent.variables[variable].dimensions

    def isel(self, **kwargs):
        """
        Selects from the array without knowledge of the dimension order

        params:
        key, value pairs where the key the the dimension name and the value is
        the slice to select.
        """
        keys = {}
        shape = self.shape
        for idx, d in enumerate(self.dims):
            keys[d] = slice(0, shape[idx])

        for k, v in kwargs.items():
            keys[k] = v

        key = []
        for d in self.dims:
            key.append(keys[d])

        return self[tuple(key)]
