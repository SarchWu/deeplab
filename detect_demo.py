
import os
from io import BytesIO
import tarfile
import tempfile
from six.moves import urllib

from matplotlib import gridspec
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

import tensorflow as tf
import sys



LABEL_NAMES = np.asarray([
    '0', '8003', '8060', '8006', '8029', '8069', '8058',
    '8064', '8062', '8063', '8032', '8030', '8079', '8080', 'ignore_label'
])

def create_pascal_label_colormap():
  """Creates a label colormap used in PASCAL VOC segmentation benchmark.

  Returns:
    A Colormap for visualizing segmentation results.
  """
  colormap = np.zeros((15, 3), dtype=int)
  ind = np.arange(15, dtype=int)

  for shift in reversed(range(8)):
    for channel in range(3):
      colormap[:, channel] |= ((ind >> channel) & 1) << shift
    ind >>= 3

  return colormap


def label_to_color_image(label):
  """Adds color defined by the dataset colormap to the label.

  Args:
    label: A 2D array with integer type, storing the segmentation label.

  Returns:
    result: A 2D array with floating type. The element of the array
      is the color indexed by the corresponding element in the input label
      to the PASCAL color map.

  Raises:
    ValueError: If label is not of rank 2 or its value is larger than color
      map maximum entry.
  """
  if label.ndim != 2:
    raise ValueError('Expect 2-D input label')

  colormap = create_pascal_label_colormap()

  if np.max(label) >= len(colormap):
    raise ValueError('label value too large.')

  return colormap[label]

FULL_LABEL_MAP = np.arange(len(LABEL_NAMES)).reshape(len(LABEL_NAMES), 1)
FULL_COLOR_MAP = label_to_color_image(FULL_LABEL_MAP)
#@title Helper methods

pb_path='frozen_graph.pb'
class DeepLabModel(object):
  """Class to load deeplab model and run inference."""

  INPUT_TENSOR_NAME = 'ImageTensor:0'
  OUTPUT_TENSOR_NAME = 'SemanticPredictions:0'
  INPUT_SIZE = 513
  #训练产生的模型导出的结果
  FROZEN_GRAPH_NAME = 'frozen_inference_graph'

  # def __init__(self, tarball_path):
  #   """Creates and loads pretrained deeplab model."""
  #   self.graph = tf.Graph()
  #
  #   graph_def = None
  #   # Extract frozen graph from tar archive.
  #   # tarball_path表示模型压缩包
  #   # demo默认下载已经训练好了的模型结果
  #   tar_file = tarfile.open(tarball_path)
  #   for tar_info in tar_file.getmembers():
  #     if self.FROZEN_GRAPH_NAME in os.path.basename(tar_info.name):
  #       file_handle = tar_file.extractfile(tar_info)
  #       graph_def = tf.GraphDef.FromString(file_handle.read())
  #       break
  #
  #   tar_file.close()
  #
  #   if graph_def is None:
  #     raise RuntimeError('Cannot find inference graph in tar archive.')
  #
  #   with self.graph.as_default():
  #     tf.import_graph_def(graph_def, name='')
  #
  #   self.sess = tf.Session(graph=self.graph)
  def __init__(self, pb_path):
      graph_def = tf.GraphDef.FromString(open('pb_path', 'rb').read())

      if graph_def is None:
          raise RuntimeError('Cannot find inference graph in tar archive.')

      with self.graph.as_default():
          tf.import_graph_def(graph_def, name='')
      self.sess = tf.Session(graph=self.graph)

  def run(self, image):
    """Runs inference on a single image.

    Args:
      image: A PIL.Image object, raw input image.

    Returns:
      resized_image: RGB image resized from original input image.
      seg_map: Segmentation map of `resized_image`.
    """
    width, height = image.size
    resize_ratio = 1.0 * self.INPUT_SIZE / max(width, height)
    target_size = (int(resize_ratio * width), int(resize_ratio * height))
    #保持输入图像的比例，并且使最长边不超过inputsize的长度
    resized_image = image.convert('RGB').resize(target_size, Image.ANTIALIAS)
    batch_seg_map = self.sess.run(
        self.OUTPUT_TENSOR_NAME,
        feed_dict={self.INPUT_TENSOR_NAME: [np.asarray(resized_image)]})
    seg_map = batch_seg_map[0]
    return resized_image, seg_map



def vis_segmentation(image, seg_map):
  """Visualizes input image, segmentation map and overlay view."""
  plt.figure(figsize=(15, 5))
  grid_spec = gridspec.GridSpec(1, 4, width_ratios=[6, 6, 6, 1])

  plt.subplot(grid_spec[0])
  plt.imshow(image)
  plt.axis('off')
  plt.title('input image')

  plt.subplot(grid_spec[1])
  seg_image = label_to_color_image(seg_map).astype(np.uint8)
  plt.imshow(seg_image)

  plt.axis('off')
  plt.title('segmentation map')

  plt.subplot(grid_spec[2])
  plt.imshow(image)
  plt.imshow(seg_image, alpha=0.7)
  plt.axis('off')
  plt.title('segmentation overlay')

  unique_labels = np.unique(seg_map)
  ax = plt.subplot(grid_spec[3])
  plt.imshow(
      FULL_COLOR_MAP[unique_labels].astype(np.uint8), interpolation='nearest')
  ax.yaxis.tick_right()
  plt.yticks(range(len(unique_labels)), LABEL_NAMES[unique_labels])
  plt.xticks([], [])
  ax.tick_params(width=0.0)
  plt.grid('off')
  plt.show()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python {} image_path model_path'.format(sys.argv[0]))
        exit()
    image_path = sys.argv[1]
    model_path = sys.argv[2]
    # load model
    model = DeepLabModel(model_path)
    orignal_im = Image.open(image_path)
    # run model
    resized_im, seg_map = model.run(orignal_im)
    vis_segmentation(resized_im, seg_map)