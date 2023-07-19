using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Manager : MonoBehaviour {
    // define a dictionary with int keys to store the Vector3[] landmarks
    public static Dictionary<int, Vector3[]> landmarksDict = new Dictionary<int, Vector3[]>();
    // define a dictionary with int keys to store last frame detected
    public static Dictionary<int, int> lastFrameDict = new Dictionary<int, int>();

}