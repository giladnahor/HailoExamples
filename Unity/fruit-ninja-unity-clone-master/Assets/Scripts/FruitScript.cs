﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class FruitScript : MonoBehaviour {

	public GameObject cut1;
	public GameObject cut2;

	public float speed_threshold = 0.5f;
	// Use this for initialization
	void Start () {
		
	}
	
	// Update is called once per frame
	void Update () {
		
	}

	void OnCollisionEnter2D (Collision2D target) {
		//get target.gameObject average speed

		//check if target.gameObject is the player and it speed is higher than threshold
		
		if ((target.gameObject.tag == "Player") && (target.gameObject.GetComponent<HandHandler>().Speed > speed_threshold)) {
			Debug.Log("Player is moving" + target.gameObject.GetComponent<HandHandler>().Speed);
			GameObject c1 = Instantiate (cut1, transform.position, Quaternion.identity) as GameObject;
			GameObject c2 = Instantiate (cut2, new Vector3 (transform.position.x - 2, transform.position.y, 0), Quaternion.identity) as GameObject;

			c1.GetComponent<Rigidbody2D> ().AddForce (new Vector2 (2f, 2f), ForceMode2D.Impulse);
			c1.GetComponent<Rigidbody2D> ().AddTorque (Random.Range (-2f, 2f), ForceMode2D.Impulse);

			c2.GetComponent<Rigidbody2D> ().AddForce (new Vector2 (2f, 2f), ForceMode2D.Impulse);
			c2.GetComponent<Rigidbody2D> ().AddTorque (Random.Range (-2f, 2f), ForceMode2D.Impulse);

			Destroy (gameObject);
			Destroy (c1, 2f);
			Destroy (c2, 2f);
			GameplayController.instance.playerScore += 1;
		}
	}

} // FruitScript