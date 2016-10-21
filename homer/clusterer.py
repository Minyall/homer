"""
clusterer.py

functions in this file take network structure expressed as
edges and translate it to network structure expressed as nested
clusters


"""

import subprocess
import glob
import pandas as pd
import os
import shutil
import tempfile
import dask.dataframe as dd

TOOLS_DIR = os.path.dirname(os.path.realpath(__file__))


class TemporaryDirectory(object):
    def __enter__(self):
        self.name = tempfile.mkdtemp()
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.name)


def find_clusters(unweighted_edge_list):
    """
    Uses COSparallel to identify new clusters from an unweighted edgelist
    Parameters
    ----------
    unweighted_edge_list: dask (or pandas) dataframe with columns 'W1' and 'W2'

    Returns
    -------
    pandas DataFrame
    """
    # repartition to be in one partition
    df = unweighted_edge_list.repartition(npartitions=1)

    # create a working directory
    with TemporaryDirectory() as dir_name:

        # write the unweighted edgelist to a file
        glob_filename = 'unweighted_edge_list.*.txt'
        edgelist_filename = glob_filename.replace('*', '0')

        df.to_csv(dir_name + '/' + glob_filename, sep=' ',
                  index=False, header=False, encoding='utf-8')

        # run .mcliques
        # for each output file, run cosparallel
        cmds = ['cd %s' % dir_name,
                '%s/./maximal_cliques %s' % (TOOLS_DIR.replace(' ', '\ '),  # there must be better ways to escape spaces
                                             edgelist_filename.replace(' ', '\ ')),
                '%s/./cos %s.mcliques' % (TOOLS_DIR.replace(' ', '\ '),
                                          edgelist_filename.replace(' ', '\ '))]

        response = subprocess.check_output(r'; '.join(cmds), shell=True)

        # read the mapping file created by 'maximal_cliques'
        map_filename = glob.glob(dir_name + '/*.map')
        mapping = pd.read_csv(map_filename[0], sep=' ', header=None,
                              names=['word', 'number'],
                              index_col='number')

        # read the community files
        community_files = glob.glob(dir_name+'/[0-9]*_communities.txt')

        cluster_list = list()

        for infile in community_files:
            k = int(os.path.basename(infile).rstrip('_communities.txt'))
            clusters = read_COS_output_file(infile, mapping)
            df = pd.DataFrame(pd.Series(clusters), columns=['Set'])
            df['k'] = k
            cluster_list.append(df)

    clusters = pd.concat(cluster_list)
    return clusters


def read_COS_output_file(infile_name, mapping):
    """
    Parameters
    ----------
    infile_name: basestring
        full path to the

    Reads an output of the COS program (there are multiple)
    and uses the
    take a file output from COS and return a dictionary
    with keys being the integer cluster name, and
    elements being a set of the keywords in that cluster"""

    # todo: this could be rewritten with dask, to read rows into a df,
    # and then sum those with the same index name.
    clusters = dict()
    with open(infile_name, 'r') as fin:
        for i, line in enumerate(fin):
            name = line.split(':')[0]  # the name of the cluster is the bit before the colon
            if name not in clusters:
                clusters[name] = set()
            # the elements of the cluster are after the colon, space delimited
            nodes = line.split(':')[1].split(' ')[:-1]
            for node in nodes:
                word = mapping.loc[int(node)]['word']
                clusters[name].add(word)
    return clusters


def iter_thresholds(df, threshold_column):
    """
    Provides an iterator over subsets of the DataFrame where the threshold column is above
    a particular value. Iterates through all possible values of the threshold column,
    in arbitrary order.

    Parameters
    ----------
    df: pandas or dask DataFrame
    threshold_column: basestring
        The name of the dataframe column to be used for selecting based upon thresholds

    Returns
    -------
        An iterator yielding DataFrames where every value of the threshold column
        is above a certain value
    """
    for threshold in df[threshold_column].unique():
        yield threshold, df[df[threshold_column] >= threshold]


def traverse_thresholds(weighted_edge_list):
    """
    The information we have from the network contains not just structure,
    but weights. These weights tell us how frequently individuals recognize
    the connections which give our network structure. As we vary the threshold
    at which edges are included, we cast a different net for structure.

    Just as n-cliques are nested within (n-1)-cliques, threshold n clusters
    are nested within threshold (n-1) clusters.

    Parameters
    ----------
    weighted_edge_list: dask DataFrame
        with columns:
        - `W1`, `W2`: The words that an edge is between
        - `Count`: the weight of the edge

    Returns
    -------

    """
    # Todo: want to do this with dask, return a dask dataframe

    clusters_collector = []
    for threshold, uw_el in iter_thresholds(weighted_edge_list, 'Count'):
        t_clusters = find_clusters(uw_el)
        t_clusters['threshold'] = threshold
        clusters_collector.append(t_clusters)

    clusters = dd.concat(clusters_collector)
    return clusters
