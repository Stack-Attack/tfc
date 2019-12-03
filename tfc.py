import maxflow
import numpy as np
import librosa as lr
# from pathos.multiprocessing import ProcessingPool as Pool
# import pyrubberband

class TFC:
    """
    This class controls all of the input, output, and processing to calculate and complete a Time-Frequency Crossfade.
    """

    def __init__(self, sr=None, n_fft=2048):
        self.parameters = {
            'sr': sr,
            'n_fft': n_fft
        }

    def load_audio(self, file, trim=True):
        """
        Loads audio from the directory given in file and returns the raw data. The sample rate used is either the
        sample rate set manually or the native sample rate of the audio if not specified.
        """
        y, sr = lr.core.load(file, sr=self.parameters['sr'])

        if not self.parameters['sr']:
            self.parameters['sr'] = sr

        if trim:
            yt, i = lr.effects.trim(y)
            return yt
        else:
            return y

    def write_audio(self, file, y):
        """
        Saves the audio data the the specified file location as a wav file.
        :param file:
        :param song:
        :param sr:
        :return:
        """
        lr.output.write_wav(file, y, sr=self.parameters['sr'])

    def stft(self, y, n_fft=2048):
        """
        Returns a discretized representation of the audio consisting of a series of complex values using a short-term
        fourier transform.
        :param y:
        :param n_fft:
        :return:
        """
        return lr.stft(y, n_fft=n_fft)

    def istft(self, yft):
        """
        Reconstructs the audio from provided stft transformed data.
        :param yft:
        :return:
        """
        return lr.core.istft(yft)

    def get_overlap(self, y1, y2, seconds):
        """
        Computes and returns the transition length in samples.
        :param y1:
        :param y2:
        :param seconds:
        :return:
        """
        samples = round(self.parameters['sr']*seconds)

        return samples

    def build_graph(self, y1ft, y2ft, loss=None):
        """
        Builds and returns a flow-graph on adjacent time-freqency bins using the provided loss function
        :param y1ft:
        :param y2ft:
        :param loss:
        :return:
        """

        def simple_loss(a1, a2, b1, b2):
            return np.linalg.norm([a1 - b1]) + np.linalg.norm([a2 - b2])

        if not loss:
            loss = simple_loss

        graph = maxflow.Graph[float]()
        node_ids = graph.add_grid_nodes((y1ft.shape[0], y1ft.shape[1]))

        # def calculate_row(row):
        #     r = []
        #
        #     for x in range(y1ft.shape[1]):
        #         if row != y1ft.shape[0] - 1:
        #             row.append([node_ids[row, x],
        #                         node_ids[row + 1, x],
        #                         loss(y1ft[row, x], y1ft[row + 1, x], y2ft[row, x], y2ft[row + 1, x]),
        #                         0])
        #
        #         if x != y1ft.shape[1] - 1:
        #             row.append([node_ids[row, x],
        #                         node_ids[row, x + 1],
        #                         loss(y1ft[row, x], y1ft[row, x + 1], y2ft[row, x], y2ft[row, x + 1]),
        #                         0])
        #     return r
        #
        # pool = Pool(8)
        #
        # for row in range(y1ft.shape[0]):
        #     graph.add_tedge(node_ids[row, 0], 999999, 0)
        #     graph.add_tedge(node_ids[row, y1ft.shape[1] - 1], 0, 999999)
        #
        # nodes = pool.imap(calculate_row, list(range(y1ft.shape[0])))
        #
        # for node in nodes:
        #     graph.add_edge(node[0], node[1], node[2], node[3])

        for row in range(y1ft.shape[0]):
           graph.add_tedge(node_ids[row, 0], 999999, 0)
           graph.add_tedge(node_ids[row, y1ft.shape[1] - 1], 0, 999999)

           for x in range(y1ft.shape[1]):
               if row != y1ft.shape[0] - 1:
                   graph.add_edge(
                       node_ids[row, x],
                       node_ids[row + 1, x],
                       loss(y1ft[row, x], y1ft[row + 1, x], y2ft[row, x], y2ft[row + 1, x]), 0)

               if x != y1ft.shape[1] - 1:
                   graph.add_edge(
                       node_ids[row, x],
                       node_ids[row, x + 1],
                       loss(y1ft[row, x], y1ft[row, x + 1], y2ft[row, x], y2ft[row, x + 1]), 0)

        return graph, node_ids

    def cut(self, graph, node_ids):
        """
        Computes the optimal graph cut.
        :param graph:
        :return:
        """
        flow = graph.maxflow()
        print("Flow = "+str(flow))
        seam = graph.get_grid_segments(node_ids)
        return seam

    def join_on_seam(self, y1ft, y2ft, seam):
        """
        Joins two stft representations of songs with equal dimensions along a found seam.
        :param y1ft:
        :param y2ft:
        :param seam:
        :return:
        """
        new_slice = np.zeros((y1ft.shape[0], y1ft.shape[1]), dtype=np.complex64)

        for row in range(seam.shape[0]):
            for x in range(seam.shape[1]):
                if seam[row, x]:
                    new_slice[row, x] = np.array(y2ft[row, x])
                    # new_slice[row,x] = 999
                else:
                    new_slice[row, x] = np.array(y1ft[row, x])
                    # new_slice[row,x] = np.array(70)

        return new_slice

    def process_TFC(self, file1, file2, seconds, trim=True, loss=None):
        """
        Given two audio files computes and returns the files transitioned along a computed seam through the time-frequency
        domain.
        :param file1:
        :param file2:
        :param seconds:
        :param trim:
        :return:
        """
        print('Loading Files...')
        y1 = self.load_audio(file1, trim)
        y2 = self.load_audio(file2, trim)

        print('Calculating overlap...')
        overlap = self.get_overlap(y1, y2, seconds)

        print('Calculating stfts...')
        y1ft = self.stft(y1[-overlap:])
        y2ft = self.stft(y2[:overlap])

        print('Building graph...')
        graph, nodes = self.build_graph(y1ft, y2ft, loss)
        print('Finding seam...')
        seam = self.cut(graph, nodes)

        print('Joining along seam...')
        new_slice = self.join_on_seam(y1ft, y2ft, seam)
        print('Reconstructing audio...')
        transition = self.istft(new_slice)

        print('DONE')
        return np.concatenate((y1[:-overlap], transition, y2[overlap:]), axis=None), transition


tfc = TFC()

final, transition = tfc.process_TFC('dj1.ogg', 'dj2.ogg', 12)

tfc.write_audio('final.wav', final)
tfc.write_audio('transition.wav', transition)































































