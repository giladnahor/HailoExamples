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
    public float scaleX = 20.0f;
    public float scaleY = 8.0f;
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
                foreach (var id in d.ids)
                {
                    if (!Manager.landmarksDict.ContainsKey(id))
                    {
                        Manager.landmarksDict.Add(id, new Vector3[17]);
                        Manager.landmarksConfidence.Add(id, new float[17]);
                        GameObject p = Instantiate (Player, new Vector3(0, 0, 0), Quaternion.identity) as GameObject;
                        UpdateTargets playerParams = p.GetComponent<UpdateTargets>();
                        playerParams.id = id;
                        // get random color
                        playerParams.color = new Color(UnityEngine.Random.Range(0.0f, 1.0f), UnityEngine.Random.Range(0.0f, 1.0f), UnityEngine.Random.Range(0.0f, 1.0f));
                    }
                    for (int i = 0; i < 17; i++)
                    {
                        Manager.landmarksDict[id][i] = new Vector3((d.landmarksX[i+(17*count)]) * scaleX, (d.landmarksY[i+(17*count)]) * scaleY, 0);
                        Manager.landmarksConfidence[id][i] = d.confidence[i+(17*count)];
                    }
                    Manager.lastFrameDict[id] = Time.frameCount;
                    // Debug.Log("id: " + id + " " + Manager.landmarksDict[id][0] + " " + Manager.landmarksDict[id][1]);
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
                    Manager.landmarksConfidence.Remove(keys[i]);
                    // Debug.Log("removed: " + keys[i]);
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