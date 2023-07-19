using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class UpdateTargets : MonoBehaviour
{
    public int id;
    public bool fullBody = false;
    public bool mirror = true;
    public bool freeze = false;
    public float smoothing = 0.5f;
    public float AvatarCenterHeight = 1.0f; // Height of the center of the body
    public float AvatarShoulderDistance = 0.34f; // Distance between shoulders used to calculate scaleX
    public float AvatarCenterNeckDistance = 0.5f; // Distance between center and neck used to calculate scaleY
    public float AvatarcenterShift = 0.05f; // Shift between hips line and center of the body
    public float AvatarNeckShift = 0.06f; // Shift between shoulders line and neck
    public Transform CenterTarget;
    public Transform LeftHandTarget;
    public Transform LeftElbowTarget;
    public Transform LeftShoulderTarget;
    public Transform RightHandTarget;
    public Transform RightElbowTarget;
    public Transform RightShoulderTarget;
    public Transform LeftLegTarget;
    public Transform LeftKneeTarget;
    public Transform LeftThighTarget;
    public Transform RightLegTarget;
    public Transform RightKneeTarget;
    public Transform RightThighTarget;
    public Transform NoseTarget;
    public Transform NeckTarget;
    
    private float scaleX = 1.0f;
    private float scaleY = 1.0f;
    // Update is called once per frame
    void Update()
    {
        if (freeze) {
            return;
        }
        // check if is in the dictionary
        if (Manager.landmarksDict.ContainsKey(id))
        {
            // update the position of the targets
            Vector3 center = Vector3.Lerp(CenterTarget.position, (Manager.landmarksDict[id][11] + Manager.landmarksDict[id][12]) / 2, smoothing);
            Vector3 neck = Vector3.Lerp(NeckTarget.position, (Manager.landmarksDict[id][5] + Manager.landmarksDict[id][6]) / 2, smoothing);
            
            CenterTarget.position = Vector3.Lerp(CenterTarget.position, center + new Vector3(0, AvatarcenterShift, 0), smoothing);
            NoseTarget.position = Vector3.Lerp(NoseTarget.position, Manager.landmarksDict[id][0] + new Vector3(0, 0, -0.8f), smoothing);
            NeckTarget.position = Vector3.Lerp(NeckTarget.position, neck+ new Vector3(0, AvatarNeckShift, 0), smoothing);
            
            if (mirror) {
                LeftHandTarget.position = Vector3.Lerp(LeftHandTarget.position, Manager.landmarksDict[id][9] + new Vector3(0, 0, -0.2f), smoothing);
                LeftElbowTarget.position = Vector3.Lerp(LeftElbowTarget.position, Manager.landmarksDict[id][7], smoothing);
                LeftShoulderTarget.position = Vector3.Lerp(LeftShoulderTarget.position, Manager.landmarksDict[id][5], smoothing);
                RightHandTarget.position = Vector3.Lerp(RightHandTarget.position, Manager.landmarksDict[id][10] + new Vector3(0, 0, -0.2f), smoothing);
                RightElbowTarget.position = Vector3.Lerp(RightElbowTarget.position, Manager.landmarksDict[id][8], smoothing);
                RightShoulderTarget.position = Vector3.Lerp(RightShoulderTarget.position, Manager.landmarksDict[id][6], smoothing);
                if (fullBody)
                {
                    LeftLegTarget.position = Vector3.Lerp(LeftLegTarget.position, Manager.landmarksDict[id][15], smoothing);
                    LeftKneeTarget.position = Vector3.Lerp(LeftKneeTarget.position, Manager.landmarksDict[id][13], smoothing);
                    LeftThighTarget.position = Vector3.Lerp(LeftThighTarget.position, Manager.landmarksDict[id][11], smoothing);
                    RightLegTarget.position = Vector3.Lerp(RightLegTarget.position, Manager.landmarksDict[id][16], smoothing);
                    RightKneeTarget.position = Vector3.Lerp(RightKneeTarget.position, Manager.landmarksDict[id][14], smoothing);
                    RightThighTarget.position = Vector3.Lerp(RightThighTarget.position, Manager.landmarksDict[id][12], smoothing);
                }
            }

            scaleY = Vector3.Distance(CenterTarget.position, NeckTarget.position) / AvatarCenterNeckDistance;
            scaleX = Vector3.Distance(LeftShoulderTarget.position, RightShoulderTarget.position) / AvatarShoulderDistance;
            // get the gameobject this script is attached to
            GameObject go = this.gameObject;
            // get the transform of the gameobject this script is attached to
            Transform t = go.transform;
            // set the scale of the gameobject this script is attached to with smooth transition
            t.localScale = Vector3.Lerp(t.localScale, new Vector3(scaleX, scaleY, (scaleX + scaleY) / 2), smoothing*0.05f);
            // set the position of the gameobject this script is attached to with smooth transition
            t.position = Vector3.Lerp(t.position, CenterTarget.position - new Vector3(0, AvatarCenterHeight * scaleY, 0), smoothing*0.05f);
            
        } else {
            // Destroy this object
            Debug.Log("Destroy " + id);
            Destroy(this.gameObject);
        }
        
        
    }
}

// Manager.centerXY = (Manager.landmarks[11] + Manager.landmarks[12]) / 2;
// Manager.neckXY = (Manager.landmarks[5] + Manager.landmarks[6]) / 2;
// // get scale by comparing distance to rig known size
// if (autoUpdateScale){
//     Manager.scale = 0.75f / Vector3.Distance(Manager.centerXY, Manager.neckXY);
//     // Manager.scale = 0.485f / Vector3.Distance(Manager.centerXY, Manager.neckXY);
// } else {
//     Manager.scale = scale;
// }
// // Make sure scale is not too small
// if (Manager.scale < 1f)
// {
//     Manager.scale = 1f;
// }
// if (Manager.scale > 7f)
// {
//     Manager.scale = 7f;
// }

// //update with scale
// Manager.centerXY = Manager.centerXY * Manager.scale;
// Manager.neckXY = Manager.neckXY * Manager.scale;
// for (int i = 0; i < 17; i++)
// {
//     Manager.landmarks[i] = Manager.landmarks[i] * Manager.scale;
// }
 