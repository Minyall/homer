from . import clusterer
from . import parser
from . import relate
from . import tree
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
                 clusters_globstring=None,
                 relations_globstring=None):
        """

        Parameters
        ----------
        weighted_edge_list_globstring

        clusters_globstring (optional)

        you need at least one of these to be able to do anything, though.

        """
        if weighted_edge_list_globstring is not None:
            self.weighted_edge_list = dd.read_hdf(weighted_edge_list_globstring,
                                                  '/weighted_edge_list')

        if clusters_globstring is not None:
            self.clusters = dd.read_hdf(clusters_globstring, '/clusters')

        if relations_globstring is not None:
            self.relations = dd.read_hdf(relations_globstring, '/relations')

    def compute_clusters(self, clusters_globstring, min_threshold):
        self.clusters = clusterer.build_cluster_db(
            self.weighted_edge_list,
            output_globstring=clusters_globstring,
            min_threshold=min_threshold
        )

    def compute_relations(self, relations_globstring):
        self.relations = relate.build_relations_db(
            clusters=self.clusters,
            output_globstring=relations_globstring
        )

    def compute_tree(self):
        # put clusters in a tree
        root = tree.Cluster('__root__')
        for ID, row in self.clusters.iterrows():
            new = tree.Cluster(contents=str(ID),
                          k=row['k'],
                          w=row['threshold'],
                          date=row['Date'])

            root.insert(new)
            if row['k'] == 3:
                root.k_children.append(new)

        # add clusters as children
        for (_, _, ID), row in self.relations.iterrows():
            node = root.find(str(ID))
            for child in row['children']:
                node.k_children.append(root.find(str(child)))

        # add leaves (words)
        for node in tree.walk_k_ancestry(root, 'bottom up'):
            if node.contents != '__root__':
                present_in_children = [m.contents for m in node.get_k_members()]
                words = self.clusters['Set'].loc[int(node.contents)].compute().values[0].split(
                    ' ')
                for leaf_word in list(set(words) - set(present_in_children)):
                    leaf = root.find(leaf_word)
                    if leaf is None:
                        leaf = tree.Cluster(leaf_word, is_leaf=True)
                        root.insert(leaf)
                    node.k_children.append(leaf)

        self.tree = root

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

    def draw_nested_sets(self, cluster_ids, depth=-1):
        """

        Parameters
        ----------
        cluster_ids
        depth

        Returns
        -------

        """

