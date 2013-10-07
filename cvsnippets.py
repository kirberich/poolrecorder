raise Exception("Oi, don't run this, it's just random bits of cv code.")

#cv.Split(frame, self.gray_image, None, None, None)
#cv.Not(frame, self.gray_image)

#cv.Smooth(self.gray_image, self.temp_image, param1=5)
#cv.Dilate(self.gray_image, self.temp_image, iterations=5)
#cv.Erode(self.temp_image, frame, iterations=5)
#cv.Laplace(self.temp_image, self.edge_image, apertureSize=5)
#cv.Canny(self.gray_image, self.edge_image, 100, 200)
#cornerMem = cv.GoodFeaturesToTrack(self.edge_image, self.eig_image, self.temp_image, 500, 0.1, 0, None, 3, False)

#for point in cornerMem:
#    center = int(point[0]), int(point[1])
#    cv.Circle(frame, (center), 2, (0,255,255))

## Calibration stuff
#frame = self.img_from_depth_frame(depth)
#frame_array = self.array(frame)
# Calculate depth layers
#dilated = numpy.zeros_like(depth)
#layer = cv2.dilate(layer, kernel)
#layer = cv2.blur(layer, (11,11))