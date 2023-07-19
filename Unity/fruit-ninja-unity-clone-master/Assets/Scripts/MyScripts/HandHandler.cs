using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class HandHandler : MonoBehaviour
{
    public GameObject blast;

	public GameObject splash;

	public float Speed;
	public float UpdateDelay = 0.5f;

    // keeping track on average speed of the hand
    
	void Awake() {
		StartCoroutine(SpeedReckoner());
	}

	
	private IEnumerator SpeedReckoner() {

		YieldInstruction timedWait = new WaitForSeconds(UpdateDelay);
		Vector3 lastPosition = transform.position;
		float lastTimestamp = Time.time;

		while (enabled) {
			yield return timedWait;

			var deltaPosition = (transform.position - lastPosition).magnitude;
			var deltaTime = Time.time - lastTimestamp;

			if (Mathf.Approximately(deltaPosition, 0f)) // Clean up "near-zero" displacement
				deltaPosition = 0f;

			Speed = deltaPosition / deltaTime;


			lastPosition = transform.position;
			lastTimestamp = Time.time;
			// Debug.Log("Speed: " + Speed);
		}
	}
    void OnCollisionEnter2D (Collision2D target) {
		// Debug.Log ("Collision");
		if (target.gameObject.tag == "Bomb") {
			GameObject b = Instantiate (blast, target.transform.position, Quaternion.identity) as GameObject;
			Destroy (b.gameObject, 2f);
			Destroy (target.gameObject);
			GameplayController.instance.playerScore -= 10;
		}

		// if (target.gameObject.tag == "Fruit") {
		// 	GameObject s = Instantiate (splash, new Vector3(target.transform.position.x -1, target.transform.position.y,0), Quaternion.identity) as GameObject;
		// 	Destroy (s.gameObject, 2f);
		// 	Destroy (target.gameObject);

		// 	int rand = Random.Range (100, 150);
		// 	GameplayController.instance.playerScore += rand;
		// }
	}
}
