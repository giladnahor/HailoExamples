using System;

[Serializable]
public struct Skeleton
{
    public float[] X;
    public float[] Y; 
    public int ID;
    
}

public struct Data
{
    public byte[] image;
    public Skeleton[] skeletons;
    public int[] ids;
    
}
