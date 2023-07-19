using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class UpdateTargets : MonoBehaviour
{
    public GameObject Hand;
    public int id;
    public Color color = Color.red;
    
    private GameObject LeftHand;
    private GameObject RightHand;
    
	void Start () {
		LeftHand = Instantiate (Hand, new Vector3 (0, 0, 0), Quaternion.identity) as GameObject;
        RightHand = Instantiate (Hand, new Vector3 (0, 0, 0), Quaternion.identity) as GameObject;
        LeftHand.GetComponent<SpriteRenderer> ().color = color;
        RightHand.GetComponent<SpriteRenderer> ().color = color;
    }
    // Update is called once per frame
    void Update()
    {
        // check if is in the dictionary
        if (Manager.landmarksDict.ContainsKey(id))
        {
            LeftHand.transform.position = LeftHand.transform.position;
            RightHand.transform.position = RightHand.transform.position;
            // Debug.Log("confidence " + Manager.landmarksConfidence[id][9]);
        } else {
            // Destroy this object
            // Debug.Log("Destroy " + id);
            Destroy(LeftHand);
            Destroy(RightHand);
            Destroy(this.gameObject);
        }
    }
}