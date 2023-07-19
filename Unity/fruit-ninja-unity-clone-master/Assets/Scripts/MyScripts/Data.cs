using System;

[Serializable]
public struct Data
{
    public byte[] image;
    public float[] landmarksX;
    public float[] landmarksY; 
    public float[] confidence; 
    public int[] ids;
    
}
