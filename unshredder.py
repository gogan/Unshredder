#!/usr/bin/python

import logging
from PIL import Image as Pil

MAX = 10 ** 9

STRIP_WIDTH = 32
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 359
SAMPLING_DISTANCE = 2

FILE_PATH = './TokyoPanoramaShredded.png'


class Strip(object):
  """Represents a strip of an image."""

  # Each strip has a left and right border:
  BORDERS = {'l': 0, 'r': STRIP_WIDTH - 1}

  def __init__(self, image, position):
    self._position = position
    self._image = image
    self._image_data = self._image.getdata()
    self._neighbors = { 'l': None, 'r': None }
    self._min_distances = { 'l': MAX, 'r': MAX }
    self._border_pixels = {}
    for border in Strip.BORDERS.keys():
      self._border_pixels[border] = []
    self._LoadBorderPixels()

  def _LoadBorderPixels(self):
    """Loads the pixels on the left and right borders."""
    for border in Strip.BORDERS.keys():
      self._LoadBorder(border)

  def _LoadBorder(self, border):
    """Loads the pixels into the given border array."""
    x = Strip.BORDERS[border]
    y = 0
    sample_count = 0
    while y < IMAGE_HEIGHT:
      border_pixel = self._GetPixelValue(x, y)
      self._border_pixels[border].append(border_pixel)
      sample_count += 1
      y = sample_count * SAMPLING_DISTANCE

  def _GetPixelValue(self, x, y):
    """Returns the pixel at the given x, y coordinates."""
    pixel = self._image_data[y * STRIP_WIDTH + x]
    return pixel

  def _NeighborDistance(self, neighbor, edge, neighbor_edge):
    """Returns the pixel distance for the given neighbor and edges."""
    neighbor_pixels = neighbor.GetBorderPixels(neighbor_edge)
    border_pixels = self.GetBorderPixels(edge)
    distance = GetDistance(neighbor_pixels, border_pixels)
    if distance < self._min_distances[edge]:
      self._min_distances[edge] = distance
      self._neighbors[edge] = neighbor
    return distance

  def NeighborDistanceRight(self, neighbor):
    """Returns the pixel distance if the neighbor is placed to the right."""
    # TODO: Optimize this by saving the distances for given neighbor strips.
    return self._NeighborDistance(neighbor, 'r', 'l')

  def NeighborDistanceLeft(self, neighbor):
    """Returns the pixel distance if the neighbor is placed to the left."""
    return self._NeighborDistance(neighbor, 'l', 'r')

  def GetBorderPixels(self, border):
    """Returns the pixel array on the given border."""
    return self._border_pixels[border]

  def GetPosition(self):
    return self._position

  def GetRightNeighbor(self):
    return self._neighbors['r']

  def GetLeftNeighbor(self):
    return self._neighbors['l']

  def GetImage(self):
    return self._image


class Image(object):
  """Represents an image."""

  def __init__(self):
    self._image = None
    self._image_data = None

  def LoadFromFile(self, file_path):
    """Loads image data from the given file_path."""
    self._image = Pil.open(file_path)
    self._image_data = self._image.getdata()

  def GetStrips(self):
    """Returns list of Strip objects from the image."""
    strip_count = 0
    strips = []
    while strip_count < IMAGE_WIDTH / STRIP_WIDTH:
      strips.append(self._GetStrip(strip_count))
      strip_count += 1
    return strips

  def Size(self):
    return self._image.size

  def _GetStrip(self, strip_number):
    """Returns the strip at strip_number as image data."""
    x1 = strip_number * STRIP_WIDTH
    x2 = x1 + STRIP_WIDTH
    crop = self._image.crop((x1, 0, x2, IMAGE_HEIGHT))
    return Strip(crop, strip_number)


def GetDistance(pixels_a, pixels_b):
  """Calculates the pixel color distance between the given pixel lists."""
  distance = 0
  for i in range(len(pixels_a)):
    a_rgb = pixels_a[i]
    b_rgb = pixels_b[i]
    # Ignore blue, green, alpha; just use red:
    for j in range(len(a_rgb)-3):
      distance += abs(a_rgb[j] - b_rgb[j])
      #distance += (a_rgb[j] - b_rgb[j]) ** 2
  return distance


def FindNeighbors(strips):
  """Finds the right and left neighbors for each strip."""
  for strip in strips:
    for inner_strip in strips:
      if strip == inner_strip:
        continue
      on_right = strip.NeighborDistanceRight(inner_strip)
      on_left = strip.NeighborDistanceLeft(inner_strip)
      logging.debug('Strips: %s, %s, on left: %s, on right: %s',
                    strip.GetPosition(), inner_strip.GetPosition(), on_left,
                    on_right)
    logging.debug('Strip: %s left=%s, right=%s', strip.GetPosition(),
                  strip._min_distances['l'], strip._min_distances['r'])

def DetectLeftEdge(strips):
  """Detects the left edge in the given list of strips."""
  for strip in strips:
    logging.debug('%s Neighbors: Right: %s, Left: %s', strip.GetPosition(),
                  strip.GetRightNeighbor().GetPosition(),
                  strip.GetLeftNeighbor().GetPosition())
    if strip.GetLeftNeighbor().GetRightNeighbor() == strip:
      logging.debug('OK match!')
    else:
      logging.debug('No match for %s', strip.GetPosition())
      return strip


def OrderStrips(image, strip, count):
  """Pastes the strips in order on the given image."""
  x = count * STRIP_WIDTH
  if x >= IMAGE_WIDTH:
    return image
  else:
    logging.debug('%s: %s', count, strip.GetPosition())
    destination = (x, 0)
    image.paste(strip.GetImage(), destination)
    return OrderStrips(image, strip.GetRightNeighbor(), count+1)


def main():

  logging.basicConfig(level=logging.DEBUG)

  img = Image()
  img.LoadFromFile(FILE_PATH)
  strips = img.GetStrips()
  strips_dict = {}

  FindNeighbors(strips)

  # Detect left edge:
  left_edge = DetectLeftEdge(strips)

  # Create the output file and populate the image with the correctly ordered
  # image strips:
  unshredded = Pil.new('RGBA', img.Size())
  unshredded = OrderStrips(unshredded, left_edge, 0)
  unshredded.save('unshredded.jpg', 'JPEG')


if __name__ == "__main__":
  main()
