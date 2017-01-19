from . import clusterer
from . import parser
import dask.dataframe as dd


def new_collection(tw_file_globstring,
                   weighted_edge_list_globstring,
                   clusters_globstring,
                   hashtags_only=False, min_threshold=1):
    """
    Processes twitter JSON data to find clusters, creates a new homer object

    Parameters
    ----------
    tw_file_globstring: raw data source
    weighted_edge_list_globstring:
        This is a globstring to describe where the weigted edgelist will be saved
    clusters_globstring
        where to save info about clusters
    hashtags_only
    min_threshold

    Returns
    -------

    """

    weighted_edge_list = parser.build_weighted_edgelist_db(
        tw_file_globstring=tw_file_globstring,
        output_globstring=weighted_edge_list_globstring,
        hashtags_only=hashtags_only
    )

    clusters = clusterer.build_cluster_db(
        weighted_edge_list,
        output_globstring=clusters_globstring,
        min_threshold=min_threshold
    )

    collection = Homer(weighted_edge_list_globstring,
                       clusters_globstring)

    return collection


class Homer(object):
    """
    This object maintains a connection to the database
    and provides methods for accessing clusters and components

    The object can be created by linking it to an existing store of
    processed data, or by
    """

    def __init__(self,
                 weighted_edge_list_globstring=None,
                 clusters_globstring=None):
        if weighted_edge_list_globstring is not None:
            self.weighted_edge_list = dd.read_hdf(weighted_edge_list_globstring,
                                                  '/weighted_edge_list')

        if clusters_globstring is not None:
            self.clusters = dd.read_hdf(clusters_globstring, '/clusters')

    def get_clusters_by_keyword(self,
                                keywords=None,
                                first_date=None,
                                last_date=None):
        """
        Retrieves clusters containing corresponding any of the given keywords,
        within the specified date range.

        Parameters
        ----------
        keywords: list of strings
            will return messages containing any of the keywords
        first_date
        last_date

        Returns
        -------
        clusters: DataFrame
        """

        date_range = self.clusters[first_date <= self.clusters['Date'] <= last_date]
        selection = date_range[date_range['Set'].apply(
            lambda x: all([kw in x for kw in keywords]))].compute()

        return selection


    def get_child_clusters(self, cluster_ids, generations=1):
        """
        For a given cluster or set of clusters
        Parameters
        ----------
        cluster_ids: list of strings
            list of ids of clusters
        generations

        Returns
        -------

        """
        raise NotImplementedError
