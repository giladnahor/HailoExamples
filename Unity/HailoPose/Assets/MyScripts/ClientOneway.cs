using AsyncIO;
using NetMQ;
using NetMQ.Sockets;
using System;
using System.Collections.Concurrent;
using System.Threading;
using UnityEngine;
using UnityEngine.UI;

public class ReceiverOneway
{
    private readonly Thread receiveThread;
    private bool running;

    public ReceiverOneway()
    {
        receiveThread = new Thread((object callback) =>
        {
            using (var socket = new PullSocket())
            // using (var socket = new SubscriberSocket())
            {
                socket.Connect("tcp://localhost:5555");

                while (running)
                {
                    // string message = socket.ReceiveFrameString();
                    string message;
                    if (socket.TryReceiveFrameString(TimeSpan.FromSeconds(1), out message))
                    {
                        Data data = JsonUtility.FromJson<Data>(message);
                        ((Action<Data>)callback)(data);
                    }
                }
            }
        });
    }

    public void Start(Action<Data> callback)
    {
        running = true;
        receiveThread.Start(callback);
    }

    public void Stop()
    {
        running = false;
        receiveThread.Join();
    }
}

public class ClientOneway : MonoBehaviour
{
    private readonly ConcurrentQueue<Action> runOnMainThread = new ConcurrentQueue<Action>();
    private ReceiverOneway receiver;
    private Texture2D tex;
    public RawImage image;
    public float scaleX = 10.0f;
    public float scaleY = 10.0f;
    public GameObject Player;
    public void Start()
    {
        tex = new Texture2D(2, 2, TextureFormat.RGB24, mipChain: false);
        image.texture = tex;

        ForceDotNet.Force();
        receiver = new ReceiverOneway();
        receiver.Start((Data d) => runOnMainThread.Enqueue(() =>
            {
                int count = 0;
                foreach (var skeleton in d.skeletons)
                {
                    Debug.Log("id: " + skeleton.ID + " " + skeleton.X[0] + " " + skeleton.Y[0]);
                    int id = skeleton.ID;
                    if (!Manager.landmarksDict.ContainsKey(id))
                    {
                        Manager.landmarksDict.Add(id, new Vector3[17]);
                        GameObject p = Instantiate (Player, new Vector3(0, 0, 0), Quaternion.Euler(0,180,0)) as GameObject;
                        UpdateTargets playerParams = p.GetComponent<UpdateTargets>();
                        playerParams.id = id;
                    }
                    for (int i = 0; i < 17; i++)
                    {
                        // Labels are in the range [0, 1] and the Y axis is inverted.

                        Manager.landmarksDict[id][i] = new Vector3((skeleton.X[i]) * scaleX, (1.0f - skeleton.Y[i]) * scaleY, 0);
                        // Manager.landmarks[i] = new Vector3(-d.landmarksX[i], d.landmarksY[i], 0) * scale;
                        // Manager.landmarks[i] = new Vector3((0.5f - d.landmarksX[i]) * scaleX, (d.landmarksY[i] - 0.5f) * scaleY, 0);
                    }
                    Manager.lastFrameDict[id] = Time.frameCount;
                    Debug.Log("id: " + id + " " + Manager.landmarksDict[id][0] + " " + Manager.landmarksDict[id][1]);
                    count++;
                }
                // Create a keys array to hold stale keys
                int[] keys = new int[Manager.lastFrameDict.Count];
                int t = 0;
                // remove stale landmarks by parsing Manager.lastFrameDict[id]
                foreach (var key in Manager.lastFrameDict.Keys)
                {
                    if (Time.frameCount - Manager.lastFrameDict[key] > 10)
                    {
                        keys[t] = key;
                        t++;
                    }   
                }
                // remove stale landmarks from Manager
                for (int i=0; i<t; i++)
                {
                    Manager.landmarksDict.Remove(keys[i]);
                    Manager.lastFrameDict.Remove(keys[i]);
                    Debug.Log("removed: " + keys[i]);
                }
                
                tex.LoadImage(d.image);
            }
        ));
    }

    public void LateUpdate()
    {
        if (!runOnMainThread.IsEmpty)
        {
            Action action;
            while (runOnMainThread.TryDequeue(out action))
            {
                action.Invoke();
            }
        }
    }

    private void OnDestroy()
    {
        receiver.Stop();
        NetMQConfig.Cleanup();
    }
}