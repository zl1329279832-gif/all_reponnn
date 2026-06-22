package com.delivery.util;

public class GridUtils {

    private static final double DEFAULT_GRID_SIZE = 0.01;

    public static String getGridCode(double latitude, double longitude) {
        return getGridCode(latitude, longitude, DEFAULT_GRID_SIZE);
    }

    public static String getGridCode(double latitude, double longitude, double gridSize) {
        int latGrid = (int) Math.floor(latitude / gridSize);
        int lngGrid = (int) Math.floor(longitude / gridSize);
        return String.format("G%d_%d", latGrid, lngGrid);
    }

    public static double[] getGridCenter(String gridCode) {
        return getGridCenter(gridCode, DEFAULT_GRID_SIZE);
    }

    public static double[] getGridCenter(String gridCode, double gridSize) {
        if (gridCode == null || !gridCode.startsWith("G")) {
            return null;
        }
        String[] parts = gridCode.substring(1).split("_");
        if (parts.length != 2) {
            return null;
        }
        int latGrid = Integer.parseInt(parts[0]);
        int lngGrid = Integer.parseInt(parts[1]);
        return new double[]{
                latGrid * gridSize + gridSize / 2,
                lngGrid * gridSize + gridSize / 2
        };
    }

    public static double distance(double lat1, double lng1, double lat2, double lng2) {
        double earthRadius = 6371000;
        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return earthRadius * c;
    }
}
